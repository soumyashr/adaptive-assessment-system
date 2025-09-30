import math
import numpy as np
from typing import List, Tuple, Dict, Optional
from collections import deque
from config import get_config
import logging

logger = logging.getLogger(__name__)


class IRTEngine:
    def __init__(self, config=None):
        self.config = config or get_config()
        irt_config = self.config.get_irt_config()
        tier_config = self.config.get_tier_config()

        # Load configuration values
        self.target_sem = irt_config["target_sem"]
        self.max_questions = irt_config["max_questions"]
        self.min_questions = irt_config["min_questions"]
        self.history_window = irt_config["history_window"]
        self.max_theta_change = irt_config["max_theta_change"]
        self.theta_jump = irt_config["theta_jump"]
        self.consecutive_same_responses = irt_config["consecutive_same_responses"]
        self.theta_bounds = irt_config["theta_bounds"]
        self.newton_raphson_iterations = irt_config["newton_raphson_iterations"]
        self.convergence_threshold = irt_config["convergence_threshold"]
        self.exponential_smoothing_alpha = irt_config["exponential_smoothing_alpha"]
        self.enable_consecutive_jumps = irt_config["enable_consecutive_jumps"]

        # UPDATED: Strict consecutive-based tier progression
        self.tier_consecutive_for_promotion = irt_config.get("tier_consecutive_for_promotion",
                                                             4)  # 4 consecutive correct
        self.tier_consecutive_for_demotion = irt_config.get("tier_consecutive_for_demotion",
                                                            4)  # 4 consecutive incorrect
        self.min_questions_before_tier_change = irt_config.get("min_questions_before_tier_change",
                                                               3)  # After 3 questions

        # Tier mappings from config
        self.tier_theta_ranges = tier_config["theta_ranges"]
        self.tier_discrimination_ranges = tier_config["discrimination_ranges"]
        self.tier_difficulty_ranges = tier_config["difficulty_ranges"]
        self.initial_theta_map = tier_config["initial_theta_map"]

        # Newton-Raphson safety constants
        self.ABSOLUTE_MAX_TOTAL_CHANGE = 1.5  # Never allow total change > 1.5 per update
        self.MIN_SECOND_DERIVATIVE = 1e-6  # Better numerical stability
        self.MAX_SINGLE_STEP = 0.8  # Absolute maximum single step
        self.PROBABILITY_EPSILON = 1e-4  # Tighter probability bounds

        # Log tier progression settings
        logger.info(f"Strict consecutive-based tier progression enabled:")
        logger.info(f"  Promotion: {self.tier_consecutive_for_promotion} consecutive correct answers")
        logger.info(f"  Demotion: {self.tier_consecutive_for_demotion} consecutive incorrect answers")
        logger.info(f"  Min questions before tier change: {self.min_questions_before_tier_change}")

    def get_initial_theta(self, competence_level: str) -> float:
        """Get initial theta based on competence level"""
        return self.initial_theta_map.get(competence_level, -1.0)

    def theta_to_tier(self, theta: float) -> str:
        """Convert theta to tier"""
        if theta < -1.0:
            return "C1"
        elif theta < 0.0:
            return "C2"
        elif theta < 1.0:
            return "C3"
        else:
            return "C4"

    def detect_consecutive_responses(self, response_history: List[bool]) -> Dict[str, any]:
        """
        Detect consecutive same responses and determine theta adjustment strategy

        Args:
            response_history: List of boolean responses (True=correct, False=incorrect)

        Returns:
            Dict with keys: 'has_consecutive', 'consecutive_count', 'response_type', 'apply_jump'
        """
        if not response_history or len(response_history) < self.consecutive_same_responses:
            return {
                'has_consecutive': False,
                'consecutive_count': 0,
                'response_type': None,
                'apply_jump': False
            }

        # Check the most recent responses
        recent_responses = response_history[-self.consecutive_same_responses:]

        # Check if all recent responses are the same
        all_correct = all(recent_responses)
        all_incorrect = all(not r for r in recent_responses)

        if all_correct or all_incorrect:
            consecutive_count = self.consecutive_same_responses
            response_type = 'correct' if all_correct else 'incorrect'

            # Count total consecutive responses of the same type from the end
            for i in range(len(response_history) - self.consecutive_same_responses - 1, -1, -1):
                if response_history[i] == recent_responses[0]:
                    consecutive_count += 1
                else:
                    break

            return {
                'has_consecutive': True,
                'consecutive_count': consecutive_count,
                'response_type': response_type,
                'apply_jump': True
            }

        return {
            'has_consecutive': False,
            'consecutive_count': 0,
            'response_type': None,
            'apply_jump': False
        }

    def calculate_theta_adjustment(self, current_theta: float, responses: List[Tuple[bool, float, float, float]],
                                   response_history: List[bool]) -> Tuple[float, Dict[str, any]]:
        """
        Calculate theta adjustment using Newton-Raphson with enhanced numerical stability
        """
        if not responses:
            return current_theta, {'method': 'no_responses', 'change': 0.0}

        # Detect consecutive responses
        consecutive_info = self.detect_consecutive_responses(response_history)

        # Enhanced Newton-Raphson calculation with safety measures
        theta = current_theta
        iterations_used = 0
        total_change = 0.0
        converged = False

        logger.debug(f"Starting Newton-Raphson: initial_theta={current_theta:.4f}")

        for iteration in range(self.newton_raphson_iterations):
            iterations_used = iteration + 1
            likelihood_derivative = 0.0
            second_derivative = 0.0

            # Calculate derivatives for all responses
            for is_correct, difficulty, discrimination, guessing in responses:
                # Enhanced probability calculation with tighter bounds
                p = self.probability_correct(theta, difficulty, discrimination, guessing)
                p = max(min(p, 1.0 - self.PROBABILITY_EPSILON), self.PROBABILITY_EPSILON)
                q = 1 - p

                # Validate discrimination parameter
                if discrimination <= 0 or discrimination > 5.0:
                    logger.warning(f"Unusual discrimination value: {discrimination}")
                    discrimination = max(0.1, min(discrimination, 3.0))

                # Standard 3PL first derivative
                if is_correct:
                    likelihood_derivative += discrimination * q / p
                else:
                    likelihood_derivative -= discrimination * p / q

                # Standard 3PL second derivative (Fisher Information)
                second_derivative -= discrimination ** 2 * p * q

            # Enhanced numerical stability checks
            if abs(second_derivative) < self.MIN_SECOND_DERIVATIVE:
                logger.debug(f"Second derivative too small: {second_derivative:.2e}, breaking")
                break

            # Calculate raw Newton-Raphson step
            raw_delta_theta = -likelihood_derivative / second_derivative

            logger.debug(f"Iteration {iteration + 1}: theta={theta:.4f}, "
                         f"L'={likelihood_derivative:.4f}, L''={second_derivative:.4f}, "
                         f"raw_delta={raw_delta_theta:.4f}")

            # ENHANCED CONVERGENCE CHECK (before clamping)
            if abs(raw_delta_theta) < self.convergence_threshold:
                logger.debug(f"Converged after {iteration + 1} iterations (raw_delta={raw_delta_theta:.6f})")
                converged = True
                break

            # Determine maximum allowed change based on consecutive responses
            if self.enable_consecutive_jumps and consecutive_info['apply_jump']:
                max_change = min(self.theta_jump, self.MAX_SINGLE_STEP)
                logger.debug(f"Applying theta jump (max_change={max_change:.4f}) due to "
                             f"{consecutive_info['consecutive_count']} consecutive "
                             f"{consecutive_info['response_type']} responses")
            else:
                max_change = min(self.max_theta_change, self.MAX_SINGLE_STEP)

            # Apply step size clamping while preserving direction
            delta_theta = raw_delta_theta
            if abs(delta_theta) > max_change:
                delta_theta = max_change if delta_theta > 0 else -max_change
                logger.debug(f"Clamped delta_theta from {raw_delta_theta:.4f} to {delta_theta:.4f}")

            # SAFETY CHECK: Prevent excessive total change accumulation
            potential_total_change = abs(total_change + delta_theta)
            if potential_total_change > self.ABSOLUTE_MAX_TOTAL_CHANGE:
                # Reduce step to stay within total change limit
                remaining_budget = self.ABSOLUTE_MAX_TOTAL_CHANGE - abs(total_change)
                delta_theta = remaining_budget if delta_theta > 0 else -remaining_budget
                logger.debug(f"Limited delta_theta to {delta_theta:.4f} due to total change budget")

                if abs(delta_theta) < self.convergence_threshold:
                    logger.debug("Total change budget exhausted, stopping iterations")
                    break

            # Apply the theta update
            new_theta = theta + delta_theta
            total_change += delta_theta

            # Apply theta bounds
            bounded_theta = max(self.theta_bounds[0], min(self.theta_bounds[1], new_theta))
            if bounded_theta != new_theta:
                logger.debug(f"Applied bounds: {new_theta:.4f} → {bounded_theta:.4f}")
                # Adjust total_change to reflect actual change
                total_change = total_change - delta_theta + (bounded_theta - theta)

            theta = bounded_theta

            # Secondary convergence check after applying bounds
            if abs(theta - (theta - delta_theta)) < self.convergence_threshold:
                logger.debug(f"Converged after bounds application")
                converged = True
                break

        # Apply exponential smoothing to prevent oscillations
        if converged or iterations_used < self.newton_raphson_iterations:
            # Less aggressive smoothing if converged
            smoothing_alpha = self.exponential_smoothing_alpha * 0.8
        else:
            # More aggressive smoothing if didn't converge
            smoothing_alpha = self.exponential_smoothing_alpha

        smoothed_theta = (smoothing_alpha * theta +
                          (1 - smoothing_alpha) * current_theta)

        logger.debug(f"Pre-smoothing theta: {theta:.4f}, post-smoothing: {smoothed_theta:.4f}")

        # Ensure final bounds
        final_theta = max(self.theta_bounds[0], min(self.theta_bounds[1], smoothed_theta))

        # Enhanced debugging and validation
        final_change = final_theta - current_theta
        if abs(final_change) > self.ABSOLUTE_MAX_TOTAL_CHANGE:
            logger.warning(f"Final change ({final_change:.4f}) exceeds maximum allowed "
                           f"({self.ABSOLUTE_MAX_TOTAL_CHANGE}), clamping")
            if final_change > 0:
                final_theta = current_theta + self.ABSOLUTE_MAX_TOTAL_CHANGE
            else:
                final_theta = current_theta - self.ABSOLUTE_MAX_TOTAL_CHANGE
            final_theta = max(self.theta_bounds[0], min(self.theta_bounds[1], final_theta))

        # Log detailed results
        if responses:
            last_response = responses[-1]
            p_correct = self.probability_correct(current_theta, last_response[1],
                                                 last_response[2], last_response[3])
            logger.info(f"Response: {'CORRECT' if last_response[0] else 'INCORRECT'} "
                        f"(P={p_correct:.3f})")
            logger.info(f"Theta update: {current_theta:.4f} → {final_theta:.4f} "
                        f"(Δ={final_theta - current_theta:+.4f})")
            logger.info(f"Converged: {converged}, Iterations: {iterations_used}")

        # Prepare comprehensive adjustment info
        adjustment_info = {
            'method': 'newton_raphson_enhanced',
            'consecutive_info': consecutive_info,
            'theta_change': final_theta - current_theta,
            'iterations_used': iterations_used,
            'converged': converged,
            'max_change_applied': self.theta_jump if consecutive_info['apply_jump'] else self.max_theta_change,
            'smoothing_applied': True,
            'smoothing_alpha': smoothing_alpha,
            'total_change_during_nr': total_change,
            'bounds_hit': final_theta in self.theta_bounds
        }

        return final_theta, adjustment_info

    def probability_correct(self, theta: float, difficulty: float,
                            discrimination: float, guessing: float = 0.25) -> float:
        """Calculate probability of correct response using 3PL model with enhanced stability"""
        try:
            # Validate inputs
            if not (-10 <= theta <= 10):
                logger.warning(f"Theta out of reasonable range: {theta}")
                theta = max(-5, min(5, theta))

            if not (0.1 <= discrimination <= 5.0):
                logger.warning(f"Discrimination out of reasonable range: {discrimination}")
                discrimination = max(0.1, min(3.0, discrimination))

            if not (0 <= guessing <= 0.5):
                logger.warning(f"Guessing parameter out of range: {guessing}")
                guessing = max(0, min(0.4, guessing))

            exponent = discrimination * (theta - difficulty)

            # Enhanced overflow/underflow protection
            if exponent > 700:  # Prevent overflow
                return 1.0
            elif exponent < -700:  # Prevent underflow
                return guessing
            else:
                exp_term = math.exp(-exponent)
                probability = guessing + (1 - guessing) / (1 + exp_term)

                # Ensure probability is in valid range
                return max(guessing, min(1.0, probability))

        except (OverflowError, ZeroDivisionError, ValueError) as e:
            logger.warning(f"Error in probability calculation: {e}")
            return 0.5

    def information(self, theta: float, difficulty: float,
                    discrimination: float, guessing: float = 0.25) -> float:
        """Calculate Fisher Information for an item with enhanced stability"""
        p = self.probability_correct(theta, difficulty, discrimination, guessing)

        if p <= guessing or p >= 1.0:
            return 0.0

        try:
            # Fisher Information for 3PL model
            q = 1 - p
            p_star = (p - guessing) / (1 - guessing)

            # Add small epsilon to prevent division by zero
            epsilon = 1e-10
            p_star = max(epsilon, min(1 - epsilon, p_star))

            numerator = (discrimination ** 2) * (p_star * (1 - p_star))
            denominator = (1 - guessing) ** 2

            information_value = numerator / denominator
            return max(0.0, min(100.0, information_value))  # Cap maximum information
        except (ZeroDivisionError, ValueError) as e:
            logger.warning(f"Error in information calculation: {e}")
            return 0.0

    def calculate_sem(self, theta: float, questions_info: List[Tuple[float, float, float]]) -> float:
        """Calculate Standard Error of Measurement"""
        total_info = 0.0
        for difficulty, discrimination, guessing in questions_info:
            total_info += self.information(theta, difficulty, discrimination, guessing)

        if total_info <= 0:
            return 1.0

        return 1.0 / math.sqrt(total_info)

    def select_next_question(self, theta: float, available_questions: List[Dict],
                             response_history: List[bool]) -> Optional[Dict]:
        """Select next question using Fisher Information and responsive tier adjustment"""
        if not available_questions:
            return None

        # Calculate current tier based on theta
        current_tier = self.theta_to_tier(theta)

        # Apply responsive tier adjustment based on recent performance
        consecutive_info = self.detect_consecutive_responses(response_history)
        adjusted_tier = self._apply_responsive_tier_adjustment(current_tier, response_history, consecutive_info)

        # Filter questions by adjusted tier
        suitable_questions = self._filter_questions_by_tier(available_questions, adjusted_tier)

        if not suitable_questions:
            # Fallback to any available question
            suitable_questions = available_questions

        # Select question with maximum Fisher Information
        best_question = None
        max_information = -1

        for question in suitable_questions:
            info = self.information(
                theta,
                question['difficulty_b'],
                question['discrimination_a'],
                question['guessing_c']
            )

            if info > max_information:
                max_information = info
                best_question = question

        logger.debug(f"Selected question with info={max_information:.3f}, tier={adjusted_tier}")
        return best_question

    def _apply_responsive_tier_adjustment(self, current_tier: str, response_history: List[bool],
                                          consecutive_info: Dict[str, any]) -> str:
        """Apply STRICT consecutive-based tier adjustment

        UPDATED: Tier changes ONLY based on consecutive responses:
        - 4 consecutive correct → tier up
        - 4 consecutive incorrect → tier down
        """

        # Allow tier adjustment after minimum questions
        if len(response_history) < self.min_questions_before_tier_change:
            logger.debug(
                f"Not enough questions for tier change: {len(response_history)}/{self.min_questions_before_tier_change}")
            return current_tier

        # Count consecutive responses from the end
        consecutive_correct = 0
        consecutive_incorrect = 0

        # Count from the most recent response backwards
        for i in range(len(response_history) - 1, -1, -1):
            if response_history[i]:  # Correct response
                if consecutive_incorrect > 0:
                    break  # Hit an opposite response, stop counting
                consecutive_correct += 1
            else:  # Incorrect response
                if consecutive_correct > 0:
                    break  # Hit an opposite response, stop counting
                consecutive_incorrect += 1

        # TIER PROMOTION: Exactly 4 consecutive correct answers
        if consecutive_correct >= self.tier_consecutive_for_promotion:
            new_tier = self._adjust_tier_up(current_tier, jumps=1)
            if new_tier != current_tier:
                logger.info(f"TIER PROMOTION: {current_tier} → {new_tier} "
                            f"({consecutive_correct} consecutive correct answers)")
                return new_tier
            else:
                logger.debug(f"Already at maximum tier (C4), cannot promote further")

        # TIER DEMOTION: Exactly 4 consecutive incorrect answers
        elif consecutive_incorrect >= self.tier_consecutive_for_demotion:
            new_tier = self._adjust_tier_down(current_tier, jumps=1)
            if new_tier != current_tier:
                logger.info(f"TIER DEMOTION: {current_tier} → {new_tier} "
                            f"({consecutive_incorrect} consecutive incorrect answers)")
                return new_tier
            else:
                logger.debug(f"Already at minimum tier (C1), cannot demote further")

        # No tier change - log current status
        else:
            if consecutive_correct > 0:
                logger.debug(
                    f"Tier unchanged at {current_tier}: {consecutive_correct}/{self.tier_consecutive_for_promotion} "
                    f"consecutive correct (need {self.tier_consecutive_for_promotion} for promotion)")
            elif consecutive_incorrect > 0:
                logger.debug(
                    f"Tier unchanged at {current_tier}: {consecutive_incorrect}/{self.tier_consecutive_for_demotion} "
                    f"consecutive incorrect (need {self.tier_consecutive_for_demotion} for demotion)")
            else:
                logger.debug(f"Tier unchanged at {current_tier}: mixed recent responses")

        return current_tier

    def _adjust_tier_up(self, tier: str, jumps: int = 1) -> str:
        """Adjust tier up by specified number of jumps"""
        tier_order = ["C1", "C2", "C3", "C4"]
        try:
            current_index = tier_order.index(tier)
            new_index = min(current_index + jumps, len(tier_order) - 1)
            return tier_order[new_index]
        except ValueError:
            logger.warning(f"Unknown tier: {tier}, defaulting to C1")
            return "C1"

    def _adjust_tier_down(self, tier: str, jumps: int = 1) -> str:
        """Adjust tier down by specified number of jumps"""
        tier_order = ["C1", "C2", "C3", "C4"]
        try:
            current_index = tier_order.index(tier)
            new_index = max(current_index - jumps, 0)
            return tier_order[new_index]
        except ValueError:
            logger.warning(f"Unknown tier: {tier}, defaulting to C1")
            return "C1"

    def _filter_questions_by_tier(self, questions: List[Dict], tier: str) -> List[Dict]:
        """Filter questions by tier-appropriate difficulty and discrimination"""
        if tier not in self.tier_difficulty_ranges:
            logger.warning(f"Unknown tier {tier}, using C1 ranges")
            tier = "C1"

        difficulty_range = self.tier_difficulty_ranges[tier]
        discrimination_range = self.tier_discrimination_ranges[tier]

        filtered = []
        for q in questions:
            difficulty_b = q.get('difficulty_b', 0.0)
            discrimination_a = q.get('discrimination_a', 1.0)

            if (difficulty_range[0] <= difficulty_b <= difficulty_range[1] and
                    discrimination_range[0] <= discrimination_a <= discrimination_range[1]):
                filtered.append(q)

        logger.debug(f"Filtered {len(filtered)}/{len(questions)} questions for tier {tier}")
        return filtered

    def update_theta(self, current_theta: float, responses: List[Tuple[bool, float, float, float]],
                     response_history: List[bool] = None) -> Tuple[float, Dict[str, any]]:
        """
        Update theta using enhanced Newton-Raphson method with consecutive response detection

        Args:
            current_theta: Current theta value
            responses: List of (is_correct, difficulty, discrimination, guessing) tuples
            response_history: List of boolean responses for consecutive detection

        Returns:
            Tuple of (new_theta, adjustment_info)
        """
        if response_history is None:
            response_history = [r[0] for r in responses]

        return self.calculate_theta_adjustment(current_theta, responses, response_history)

    def should_stop_assessment(self, sem: float, questions_asked: int,
                               response_history: List[bool], current_theta: float = None) -> bool:
        """Determine if assessment should stop

        FIXED: Only allow early termination for consecutive correct if at maximum proficiency
        """
        # Minimum questions check
        if questions_asked < self.min_questions:
            return False

        # Maximum questions check
        if questions_asked >= self.max_questions:
            return True

        # SEM threshold check
        if sem <= self.target_sem:
            return True

        # FIXED: Enhanced stopping criteria with tier awareness
        if len(response_history) >= 8:
            consecutive_info = self.detect_consecutive_responses(response_history)

            # Only allow early termination for consecutive correct if at C4 (expert) level
            if consecutive_info['consecutive_count'] >= 6:
                # Check if we're at maximum proficiency
                if current_theta is not None:
                    current_tier = self.theta_to_tier(current_theta)

                    if consecutive_info['response_type'] == 'correct' and current_tier == 'C4':
                        # At maximum tier with many consecutive correct - can terminate
                        logger.info(f"Early termination: {consecutive_info['consecutive_count']} "
                                    f"consecutive correct at maximum proficiency (C4)")
                        return True
                    elif consecutive_info['response_type'] == 'incorrect' and current_tier == 'C1':
                        # At minimum tier with many consecutive incorrect - can terminate
                        logger.info(f"Early termination: {consecutive_info['consecutive_count']} "
                                    f"consecutive incorrect at minimum proficiency (C1)")
                        return True
                    else:
                        # Don't terminate - there are still higher/lower tiers to explore
                        logger.debug(f"Not terminating despite {consecutive_info['consecutive_count']} "
                                     f"consecutive {consecutive_info['response_type']} - "
                                     f"current tier {current_tier} can still be adjusted")

            # Standard consistency check for perfect/zero performance
            recent_responses = response_history[-8:]
            accuracy = sum(recent_responses) / len(recent_responses)

            # Only terminate on perfect/zero if we've tested enough questions
            if questions_asked >= 15:
                if accuracy == 1.0:
                    if current_theta is not None and self.theta_to_tier(current_theta) == 'C4':
                        return True  # Perfect at max level
                elif accuracy == 0.0:
                    if current_theta is not None and self.theta_to_tier(current_theta) == 'C1':
                        return True  # Zero at min level

        return False

    def calculate_assessment_metrics(self, responses: List[Tuple[bool, float, float, float]],
                                     final_theta: float, response_history: List[bool] = None) -> Dict:
        """Calculate final assessment metrics with consecutive response analysis"""
        if not responses:
            return {
                "accuracy": 0.0,
                "total_information": 0.0,
                "average_difficulty": 0.0,
                "consecutive_patterns": {},
                "tier_progression": {}
            }

        correct_count = sum(1 for r, _, _, _ in responses if r)
        accuracy = correct_count / len(responses)

        total_info = sum(
            self.information(final_theta, difficulty, discrimination, guessing)
            for _, difficulty, discrimination, guessing in responses
        )

        avg_difficulty = sum(difficulty for _, difficulty, _, _ in responses) / len(responses)

        # Analyze consecutive patterns
        consecutive_patterns = {}
        tier_progression = {}

        if response_history:
            consecutive_info = self.detect_consecutive_responses(response_history)
            consecutive_patterns = {
                "max_consecutive_correct": self._count_max_consecutive(response_history, True),
                "max_consecutive_incorrect": self._count_max_consecutive(response_history, False),
                "final_consecutive_info": consecutive_info
            }

            # Analyze tier progression metrics with consecutive-based system
            if len(response_history) >= self.min_questions_before_tier_change:
                # Count consecutive responses from the end
                consecutive_correct = 0
                consecutive_incorrect = 0
                for i in range(len(response_history) - 1, -1, -1):
                    if response_history[i]:
                        if consecutive_incorrect > 0:
                            break
                        consecutive_correct += 1
                    else:
                        if consecutive_correct > 0:
                            break
                        consecutive_incorrect += 1

                tier_progression = {
                    "consecutive_correct": consecutive_correct,
                    "consecutive_incorrect": consecutive_incorrect,
                    "promotion_threshold": self.tier_consecutive_for_promotion,
                    "demotion_threshold": self.tier_consecutive_for_demotion,
                    "meets_promotion_criteria": consecutive_correct >= self.tier_consecutive_for_promotion,
                    "meets_demotion_criteria": consecutive_incorrect >= self.tier_consecutive_for_demotion
                }

        return {
            "accuracy": accuracy,
            "total_information": total_info,
            "average_difficulty": avg_difficulty,
            "questions_count": len(responses),
            "correct_count": correct_count,
            "consecutive_patterns": consecutive_patterns,
            "tier_progression": tier_progression
        }

    def _count_max_consecutive(self, response_history: List[bool], target_response: bool) -> int:
        """Count maximum consecutive responses of a specific type"""
        if not response_history:
            return 0

        max_consecutive = 0
        current_consecutive = 0

        for response in response_history:
            if response == target_response:
                current_consecutive += 1
                max_consecutive = max(max_consecutive, current_consecutive)
            else:
                current_consecutive = 0

        return max_consecutive