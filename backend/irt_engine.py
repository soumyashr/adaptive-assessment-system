"""
Enhanced IRT (Item Response Theory) Engine for Adaptive Assessment

Key Features:
- Adaptive question selection based on current ability (theta) estimation
- Conservative tier progression (single-tier jumps only)
- Multiple test purposes (Screening, Diagnostic, Placement)
- Content balancing and item exposure control (optional)
- Response time integration (optional)
- Robust error recovery with EAP/MLE fallbacks
- Comprehensive diagnostic reporting
- Performance optimization with caching

IMPORTANT FIX (NO OTHER FILES NEED CHANGES):
This version handles the 'tuple' object has no attribute 'get' error gracefully.
The engine will work with your existing code without any modifications to services.py or other files.

Content area analysis will be automatically skipped if question_details are not provided.
Your existing calls like:
    metrics = engine.calculate_assessment_metrics(responses, final_theta)
will work perfectly fine - they just won't include content area analysis.

If you want content area analysis in the future, you can optionally add question_details:
    metrics = engine.calculate_assessment_metrics(
        responses=responses,
        final_theta=final_theta,
        question_details=[{'topic': 'algebra'}, ...]  # Optional
    )

Usage Examples:
    # Method 1: Using default config (works with your existing code)
    engine = IRTEngine()

    # Method 2: Using dictionary config
    config = {
        "irt_config": {...},
        "tier_config": {...}
    }
    engine = IRTEngine(config=config)

    # Method 3: Your existing call will work without any changes
    metrics = engine.calculate_assessment_metrics(
        responses=responses,  # Your existing response tuples
        final_theta=final_theta  # Your existing final theta
    )
    # No error! Content analysis will be skipped gracefully.
"""

import math
import numpy as np
from typing import List, Tuple, Dict, Optional, Any
from collections import deque
from functools import lru_cache
from enum import Enum
from dataclasses import dataclass
import logging
import time
import random

logger = logging.getLogger(__name__)


class TestPurpose(Enum):
    """Enum for different test purposes with specific configurations"""
    SCREENING = "screening"
    DIAGNOSTIC = "diagnostic"
    PLACEMENT = "placement"


@dataclass
class AdaptiveConfig:
    """Configuration class for different test purposes"""
    min_questions: int
    max_questions: int
    target_sem: float
    tier_change_aggressive: bool
    enable_content_balancing: bool = True
    enable_response_time: bool = False

    @classmethod
    def get_config(cls, purpose: TestPurpose):
        """Get configuration based on test purpose"""
        configs = {
            TestPurpose.SCREENING: cls(
                min_questions=5,
                max_questions=15,
                target_sem=0.5,
                tier_change_aggressive=True,
                enable_content_balancing=False
            ),
            TestPurpose.DIAGNOSTIC: cls(
                min_questions=15,
                max_questions=40,
                target_sem=0.25,
                tier_change_aggressive=False,
                enable_content_balancing=True
            ),
            TestPurpose.PLACEMENT: cls(
                min_questions=10,
                max_questions=25,
                target_sem=0.35,
                tier_change_aggressive=False,
                enable_content_balancing=True
            )
        }
        return configs.get(purpose, configs[TestPurpose.DIAGNOSTIC])


class IRTEngine:
    """
    IMPORTANT: This version is fully backward compatible and requires NO changes to other files.
    The AttributeError: 'tuple' object has no attribute 'get' is fixed by making content
    analysis optional and gracefully handling missing question_details.

    Quick fix for existing code:
        # Option 1: Just use as-is (content analysis will be skipped)
        engine = IRTEngine()
        metrics = engine.calculate_assessment_metrics(responses, final_theta)

        # Option 2: Use the simple factory (safest)
        from irt_engine import create_simple_irt_engine
        engine = create_simple_irt_engine()
        metrics = engine.calculate_assessment_metrics(responses, final_theta)
    """

    def __init__(self, config=None, test_purpose: TestPurpose = TestPurpose.DIAGNOSTIC):
        # Handle both dictionary config and object config
        if config is None:
            config = get_default_config()

        self.config = config
        self.test_purpose = test_purpose
        self.adaptive_config = AdaptiveConfig.get_config(test_purpose)

        # Track current theta throughout assessment
        self.current_theta = None

        # Handle different config formats
        if isinstance(config, dict):
            # Check if it's already in the right format
            if 'irt_config' in config and 'tier_config' in config:
                irt_config = config['irt_config']
                tier_config = config['tier_config']
            # Check if it has the methods as keys (legacy format)
            elif 'get_irt_config' in config and 'get_tier_config' in config:
                irt_config = config['get_irt_config']() if callable(config['get_irt_config']) else config['get_irt_config']
                tier_config = config['get_tier_config']() if callable(config['get_tier_config']) else config['get_tier_config']
            else:
                # Assume the dict itself is the irt_config for backward compatibility
                irt_config = config
                tier_config = get_default_config()['tier_config']
        else:
            # Object with methods
            try:
                irt_config = config.get_irt_config()
                tier_config = config.get_tier_config()
            except AttributeError:
                # Try to extract from object attributes
                if hasattr(config, 'irt_config'):
                    irt_config = config.irt_config
                    tier_config = config.tier_config if hasattr(config, 'tier_config') else get_default_config()['tier_config']
                else:
                    raise ValueError("Config must be a dict with 'irt_config' and 'tier_config' keys, "
                                   "or an object with get_irt_config() and get_tier_config() methods")

        # Load configuration values
        self.target_sem = self.adaptive_config.target_sem
        self.max_questions = self.adaptive_config.max_questions
        self.min_questions = self.adaptive_config.min_questions

        self.history_window = irt_config["history_window"]
        self.max_theta_change = irt_config["max_theta_change"]
        self.theta_jump = irt_config["theta_jump"]
        self.consecutive_same_responses = irt_config["consecutive_same_responses"]
        self.theta_bounds = irt_config["theta_bounds"]
        self.newton_raphson_iterations = irt_config["newton_raphson_iterations"]
        self.convergence_threshold = irt_config["convergence_threshold"]
        self.exponential_smoothing_alpha = irt_config["exponential_smoothing_alpha"]
        self.enable_consecutive_jumps = irt_config["enable_consecutive_jumps"]

        # Conservative tier progression settings
        self.tier_promotion_window = irt_config.get("tier_promotion_window", 8)
        self.tier_promotion_threshold = irt_config.get("tier_promotion_threshold", 6)
        self.tier_demotion_window = irt_config.get("tier_demotion_window", 8)
        self.tier_demotion_threshold = irt_config.get("tier_demotion_threshold", 2)
        self.min_questions_before_tier_change = irt_config.get("min_questions_before_tier_change", 8)

        # Tier mappings from config
        self.tier_theta_ranges = tier_config["theta_ranges"]
        self.tier_discrimination_ranges = tier_config["discrimination_ranges"]
        self.tier_difficulty_ranges = tier_config["difficulty_ranges"]
        self.initial_theta_map = tier_config["initial_theta_map"]

        # Newton-Raphson safety constants
        self.ABSOLUTE_MAX_TOTAL_CHANGE = 1.5
        self.MIN_SECOND_DERIVATIVE = 1e-6
        self.MAX_SINGLE_STEP = 0.8
        self.PROBABILITY_EPSILON = 1e-4

        # Performance optimization
        self._information_cache = {}
        self._probability_cache = {}

        # Content balancing tracking
        self.used_content_areas = {}

        # Response time tracking
        self.response_times = []

        # Theta history for stability analysis
        self.theta_history = []

        # Item exposure control
        self.item_exposure_counts = {}
        self.max_item_exposure_rate = 0.3

        logger.info(f"IRTEngine initialized for {test_purpose.value} purpose")
        logger.info(f"Configuration: min_q={self.min_questions}, max_q={self.max_questions}, "
                   f"target_sem={self.target_sem}")

    def get_initial_theta(self, competence_level: str) -> float:
        """Get initial theta based on competence level"""
        initial_theta = self.initial_theta_map.get(competence_level, -1.0)
        self.current_theta = initial_theta  # Track current theta
        self.theta_history = [initial_theta]  # Start theta history
        logger.info(f"Initial theta set to {initial_theta:.3f} for competence level '{competence_level}'")
        return initial_theta

    def initialize_assessment(self, competence_level: str = "intermediate") -> float:
        """Initialize assessment with starting theta based on competence level"""
        initial_theta = self.get_initial_theta(competence_level)
        logger.info(f"Assessment initialized with theta={initial_theta:.3f}")
        return initial_theta

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

    @lru_cache(maxsize=1000)
    def cached_probability_correct(self, theta: float, difficulty: float,
                                  discrimination: float, guessing: float = 0.25) -> float:
        """Cached version of probability calculation for performance"""
        return self.probability_correct(theta, difficulty, discrimination, guessing)

    def probability_correct(self, theta: float, difficulty: float,
                          discrimination: float, guessing: float = 0.25) -> float:
        """Calculate probability of correct response using 3PL model"""
        try:
            # Validate inputs
            theta = max(-5, min(5, theta))
            discrimination = max(0.1, min(3.0, discrimination))
            guessing = max(0, min(0.4, guessing))

            exponent = discrimination * (theta - difficulty)

            if exponent > 700:
                return 1.0
            elif exponent < -700:
                return guessing
            else:
                exp_term = math.exp(-exponent)
                probability = guessing + (1 - guessing) / (1 + exp_term)
                return max(guessing, min(1.0, probability))

        except (OverflowError, ZeroDivisionError, ValueError) as e:
            logger.warning(f"Error in probability calculation: {e}")
            return 0.5

    def information(self, theta: float, difficulty: float,
                   discrimination: float, guessing: float = 0.25) -> float:
        """Calculate Fisher Information with caching"""
        cache_key = (round(theta, 3), round(difficulty, 3),
                    round(discrimination, 3), round(guessing, 3))

        if cache_key in self._information_cache:
            return self._information_cache[cache_key]

        p = self.probability_correct(theta, difficulty, discrimination, guessing)

        if p <= guessing or p >= 1.0:
            info_value = 0.0
        else:
            try:
                q = 1 - p
                p_star = (p - guessing) / (1 - guessing)
                epsilon = 1e-10
                p_star = max(epsilon, min(1 - epsilon, p_star))

                numerator = (discrimination ** 2) * (p_star * (1 - p_star))
                denominator = (1 - guessing) ** 2
                info_value = min(100.0, numerator / denominator)
            except (ZeroDivisionError, ValueError) as e:
                logger.warning(f"Error in information calculation: {e}")
                info_value = 0.0

        self._information_cache[cache_key] = info_value
        return info_value

    def adaptive_theta_jump_size(self, consecutive_count: int,
                                response_type: str) -> float:
        """Dynamic jump size based on pattern strength"""
        base_jump = self.theta_jump

        if consecutive_count <= 3:
            return base_jump * 0.5
        elif consecutive_count <= 5:
            return base_jump * 0.75
        elif consecutive_count <= 7:
            return base_jump
        else:
            return min(base_jump * 1.25, self.MAX_SINGLE_STEP)

    def detect_consecutive_responses(self, response_history: List[bool]) -> Dict[str, Any]:
        """Detect consecutive same responses with adaptive jump sizing"""
        if not response_history or len(response_history) < self.consecutive_same_responses:
            return {
                'has_consecutive': False,
                'consecutive_count': 0,
                'response_type': None,
                'apply_jump': False,
                'jump_size': 0.0
            }

        recent_responses = response_history[-self.consecutive_same_responses:]
        all_correct = all(recent_responses)
        all_incorrect = all(not r for r in recent_responses)

        if all_correct or all_incorrect:
            consecutive_count = self.consecutive_same_responses
            response_type = 'correct' if all_correct else 'incorrect'

            # Count total consecutive
            for i in range(len(response_history) - self.consecutive_same_responses - 1, -1, -1):
                if response_history[i] == recent_responses[0]:
                    consecutive_count += 1
                else:
                    break

            jump_size = self.adaptive_theta_jump_size(consecutive_count, response_type)

            return {
                'has_consecutive': True,
                'consecutive_count': consecutive_count,
                'response_type': response_type,
                'apply_jump': True,
                'jump_size': jump_size
            }

        return {
            'has_consecutive': False,
            'consecutive_count': 0,
            'response_type': None,
            'apply_jump': False,
            'jump_size': 0.0
        }

    def select_next_question_with_content_balance(self, theta: float,
                                                 available_questions: List[Dict],
                                                 response_history: List[bool]) -> Optional[Dict]:
        """Select next question with content balancing and exposure control based on current theta"""
        if not available_questions:
            return None

        # Use current theta to determine appropriate tier
        current_tier = self.theta_to_tier(theta)
        consecutive_info = self.detect_consecutive_responses(response_history)

        # Apply fairness constraints to determine adjusted tier
        adjusted_tier = self._apply_conservative_fairness_constraints(
            current_tier, response_history, consecutive_info
        )

        logger.debug(f"Selecting question for theta={theta:.3f}, tier={current_tier}, adjusted_tier={adjusted_tier}")

        # Filter by tier based on current theta
        suitable_questions = self._filter_questions_by_tier(available_questions, adjusted_tier)
        if not suitable_questions:
            # If no questions in adjusted tier, try current tier
            suitable_questions = self._filter_questions_by_tier(available_questions, current_tier)
            if not suitable_questions:
                # Last resort: use all available questions
                suitable_questions = available_questions
                logger.warning(f"No tier-appropriate questions found, using all {len(available_questions)} available")

        # Calculate information for each question at current theta
        question_scores = []
        for question in suitable_questions:
            # Calculate Fisher Information at current theta
            info = self.information(
                theta,  # Using current theta for information calculation
                question['difficulty_b'],
                question['discrimination_a'],
                question['guessing_c']
            )

            # Content area penalty
            if self.adaptive_config.enable_content_balancing:
                content_area = question.get('content_area', 'default')
                usage_count = self.used_content_areas.get(content_area, 0)
                content_penalty = 1.0 - (0.1 * min(usage_count, 5))
            else:
                content_penalty = 1.0

            # Exposure control penalty
            item_id = question.get('id', str(question))
            exposure_count = self.item_exposure_counts.get(item_id, 0)
            exposure_penalty = 1.0 - (0.2 * min(exposure_count, 3))

            # Combined score (information at current theta with penalties)
            adjusted_score = info * content_penalty * exposure_penalty

            # Also calculate distance from optimal difficulty (theta)
            difficulty_distance = abs(question['difficulty_b'] - theta)

            question_scores.append({
                'question': question,
                'adjusted_score': adjusted_score,
                'raw_information': info,
                'difficulty_distance': difficulty_distance,
                'content_penalty': content_penalty,
                'exposure_penalty': exposure_penalty
            })

        # Select best question based on adjusted score
        if question_scores:
            # Sort by adjusted score (highest first)
            question_scores.sort(key=lambda x: x['adjusted_score'], reverse=True)

            # Select the best question
            best_item = question_scores[0]
            best_question = best_item['question']

            # Update tracking
            content_area = best_question.get('content_area', 'default')
            self.used_content_areas[content_area] = self.used_content_areas.get(content_area, 0) + 1

            item_id = best_question.get('id', str(best_question))
            self.item_exposure_counts[item_id] = self.item_exposure_counts.get(item_id, 0) + 1

            logger.info(f"Selected question: difficulty={best_question['difficulty_b']:.3f}, "
                       f"discrimination={best_question['discrimination_a']:.3f}, "
                       f"info={best_item['raw_information']:.3f}, "
                       f"adjusted_score={best_item['adjusted_score']:.3f}, "
                       f"distance_from_theta={best_item['difficulty_distance']:.3f}")

            return best_question

        return None

    def select_next_question(self, theta: float, available_questions: List[Dict],
                            response_history: List[bool]) -> Optional[Dict]:
        """Main question selection method"""
        if self.adaptive_config.enable_content_balancing:
            return self.select_next_question_with_content_balance(
                theta, available_questions, response_history
            )
        else:
            # Fallback to original selection logic
            return self._select_next_question_original(theta, available_questions, response_history)

    def _select_next_question_original(self, theta: float, available_questions: List[Dict],
                                      response_history: List[bool]) -> Optional[Dict]:
        """Original question selection logic based on current theta"""
        if not available_questions:
            return None

        # Use current theta to determine tier
        current_tier = self.theta_to_tier(theta)
        consecutive_info = self.detect_consecutive_responses(response_history)

        # Apply tier adjustment based on performance
        adjusted_tier = self._apply_conservative_fairness_constraints(
            current_tier, response_history, consecutive_info
        )

        logger.debug(f"Original selection: theta={theta:.3f}, current_tier={current_tier}, "
                    f"adjusted_tier={adjusted_tier}")

        # Filter questions by adjusted tier
        suitable_questions = self._filter_questions_by_tier(available_questions, adjusted_tier)
        if not suitable_questions:
            # Try current tier if adjusted tier has no questions
            suitable_questions = self._filter_questions_by_tier(available_questions, current_tier)
            if not suitable_questions:
                # Use all available as fallback
                suitable_questions = available_questions

        best_question = None
        max_information = -1
        best_difficulty_distance = float('inf')

        # Find question with maximum information at current theta
        for question in suitable_questions:
            # Calculate Fisher Information at current theta
            info = self.information(
                theta,  # Using current theta
                question['difficulty_b'],
                question['discrimination_a'],
                question['guessing_c']
            )

            # Also consider how close the difficulty is to current theta
            # Questions with difficulty close to theta provide most information
            difficulty_distance = abs(question['difficulty_b'] - theta)

            # Prefer higher information, but if information is similar,
            # prefer questions closer to current ability
            if info > max_information or (info == max_information and difficulty_distance < best_difficulty_distance):
                max_information = info
                best_question = question
                best_difficulty_distance = difficulty_distance

        if best_question:
            logger.info(f"Selected question: difficulty={best_question['difficulty_b']:.3f}, "
                       f"discrimination={best_question['discrimination_a']:.3f}, "
                       f"info={max_information:.3f} at theta={theta:.3f}")

        return best_question

    def robust_theta_update(self, current_theta: float,
                          responses: List[Tuple[bool, float, float, float]],
                          response_history: List[bool] = None,
                          response_times: List[float] = None) -> Tuple[float, Dict]:
        """Robust theta update with multiple fallback strategies"""
        try:
            # Try Newton-Raphson first
            new_theta, info = self.calculate_theta_adjustment(
                current_theta, responses, response_history
            )

            # Sanity check
            if abs(new_theta - current_theta) > 2.5:
                logger.warning(f"Large theta change detected: {current_theta:.3f} -> {new_theta:.3f}")
                # Use EAP estimate as fallback
                new_theta = self.calculate_eap_estimate(responses, current_theta)
                info['method'] = 'eap_fallback'
                info['original_nr_theta'] = new_theta

            # Apply response time adjustment if available
            if self.adaptive_config.enable_response_time and response_times:
                time_adjustment = self.calculate_response_time_adjustment(
                    new_theta, responses, response_times
                )
                new_theta += time_adjustment
                info['response_time_adjustment'] = time_adjustment

        except Exception as e:
            logger.error(f"Newton-Raphson failed: {e}, using MLE")
            new_theta = self.calculate_mle_estimate(responses, current_theta)
            info = {'method': 'mle_fallback', 'error': str(e)}

        # Update theta history
        self.theta_history.append(new_theta)

        return new_theta, info

    def calculate_eap_estimate(self, responses: List[Tuple[bool, float, float, float]],
                              prior_theta: float = 0.0) -> float:
        """Expected A Posteriori estimate as fallback"""
        # Simple EAP implementation
        theta_range = np.linspace(self.theta_bounds[0], self.theta_bounds[1], 100)
        prior = np.exp(-0.5 * (theta_range - prior_theta) ** 2) / np.sqrt(2 * np.pi)

        likelihood = np.ones_like(theta_range)
        for is_correct, difficulty, discrimination, guessing in responses:
            for i, theta in enumerate(theta_range):
                p = self.probability_correct(theta, difficulty, discrimination, guessing)
                if is_correct:
                    likelihood[i] *= p
                else:
                    likelihood[i] *= (1 - p)

        posterior = likelihood * prior
        posterior /= np.sum(posterior)

        eap_theta = np.sum(theta_range * posterior)
        return float(eap_theta)

    def calculate_mle_estimate(self, responses: List[Tuple[bool, float, float, float]],
                              initial_theta: float = 0.0) -> float:
        """Maximum Likelihood Estimate as fallback"""
        # Simple grid search for MLE
        theta_range = np.linspace(self.theta_bounds[0], self.theta_bounds[1], 200)
        log_likelihoods = []

        for theta in theta_range:
            log_likelihood = 0.0
            for is_correct, difficulty, discrimination, guessing in responses:
                p = self.probability_correct(theta, difficulty, discrimination, guessing)
                if is_correct:
                    log_likelihood += np.log(max(p, 1e-10))
                else:
                    log_likelihood += np.log(max(1 - p, 1e-10))
            log_likelihoods.append(log_likelihood)

        best_idx = np.argmax(log_likelihoods)
        return float(theta_range[best_idx])

    def calculate_response_time_adjustment(self, theta: float,
                                         responses: List[Tuple[bool, float, float, float]],
                                         response_times: List[float]) -> float:
        """Calculate theta adjustment based on response times"""
        if len(responses) != len(response_times):
            return 0.0

        adjustments = []
        for (is_correct, difficulty, _, _), response_time in zip(responses, response_times):
            # Expected response time model (simplified)
            expected_time = 5.0 + 2.0 * abs(theta - difficulty)
            time_ratio = response_time / expected_time

            if is_correct and time_ratio < 0.7:  # Fast and correct
                adjustments.append(0.05)  # Slight upward adjustment
            elif not is_correct and time_ratio > 1.5:  # Slow and incorrect
                adjustments.append(-0.05)  # Slight downward adjustment
            elif is_correct and time_ratio > 2.0:  # Very slow but correct (guessing?)
                adjustments.append(-0.02)

        return sum(adjustments)

    def should_stop_with_confidence(self, sem: float, questions_asked: int,
                                   response_history: List[bool]) -> Tuple[bool, float]:
        """Enhanced stopping logic with confidence estimation"""

        # Check minimum questions
        if questions_asked < self.min_questions:
            return False, 0.0

        # Check maximum questions
        if questions_asked >= self.max_questions:
            confidence = 1.0 - sem if sem < 1.0 else 0.5
            return True, confidence

        # Check theta stability
        if len(self.theta_history) >= 5:
            recent_thetas = self.theta_history[-5:]
            theta_variance = np.var(recent_thetas)
            if theta_variance < 0.01:
                logger.info(f"Theta stabilized with variance {theta_variance:.4f}")
                return True, 0.95

        # Check SEM target
        if sem <= self.target_sem:
            confidence = min(0.99, 1.0 - sem)
            return True, confidence

        # Check extreme consecutive patterns
        if len(response_history) >= 8:
            consecutive_info = self.detect_consecutive_responses(response_history)
            if consecutive_info['consecutive_count'] >= 6:
                confidence = 0.85 if consecutive_info['response_type'] == 'correct' else 0.80
                logger.info(f"Stopping due to {consecutive_info['consecutive_count']} "
                          f"consecutive {consecutive_info['response_type']} responses")
                return True, confidence

            # Check recent window consistency
            recent = response_history[-8:]
            accuracy = sum(recent) / len(recent)
            if accuracy == 1.0 or accuracy == 0.0:
                return True, 0.90

        return False, 0.0

    def should_stop_assessment(self, sem: float, questions_asked: int,
                              response_history: List[bool]) -> bool:
        """Main stopping decision method"""
        should_stop, confidence = self.should_stop_with_confidence(
            sem, questions_asked, response_history
        )
        return should_stop

    def generate_diagnostic_report(self, final_theta: float,
                                  responses: List[Tuple[bool, float, float, float]],
                                  response_history: List[bool],
                                  response_times: List[float] = None,
                                  question_details: List[Dict] = None) -> Dict:
        """
        Generate comprehensive diagnostic report

        Args:
            final_theta: Final ability estimate
            responses: List of (is_correct, difficulty, discrimination, guessing) tuples
            response_history: List of boolean responses
            response_times: Optional list of response times
            question_details: Optional list of question dictionaries with content_area info
        """

        # Basic metrics
        if not responses:
            return {
                'final_ability': final_theta,
                'final_tier': self.theta_to_tier(final_theta),
                'questions_answered': 0,
                'test_completed': False
            }

        correct_count = sum(1 for r, _, _, _ in responses if r)
        total_questions = len(responses)
        questions_asked = total_questions  # Fix: Define questions_asked
        accuracy = correct_count / total_questions

        # Calculate confidence interval
        final_sem = self.calculate_sem(
            final_theta,
            [(d, a, g) for _, d, a, g in responses]
        )
        confidence_interval = (
            final_theta - 1.96 * final_sem,
            final_theta + 1.96 * final_sem
        )

        # Content area analysis - SAFELY handle missing question_details
        content_performance = {}
        if self.adaptive_config.enable_content_balancing:
            # Check if we can do content analysis
            if question_details and isinstance(question_details, list):
                # Group questions by content area
                content_areas_data = {}
                for i, (is_correct, _, _, _) in enumerate(responses):
                    if i < len(question_details):
                        q_detail = question_details[i]
                        area = q_detail.get('content_area', q_detail.get('topic', 'default'))
                        if area not in content_areas_data:
                            content_areas_data[area] = []
                        content_areas_data[area].append(is_correct)

                # Calculate performance by area
                for area, area_responses in content_areas_data.items():
                    if area_responses:
                        area_accuracy = sum(area_responses) / len(area_responses)
                        content_performance[area] = {
                            'questions': len(area_responses),
                            'accuracy': area_accuracy,
                            'strength_level': 'Strong' if area_accuracy > 0.75 else
                                            'Weak' if area_accuracy < 0.40 else 'Moderate'
                        }
            elif hasattr(self, 'used_content_areas') and self.used_content_areas:
                # Fallback: Use tracked content areas if available
                # This provides basic content area tracking without detailed analysis
                for area in self.used_content_areas:
                    content_performance[area] = {
                        'questions': self.used_content_areas[area],
                        'accuracy': None,  # Can't calculate without question details
                        'strength_level': 'Unknown'
                    }
            # If no content data available, just skip content analysis silently

        # Analyze response patterns
        consecutive_info = self.detect_consecutive_responses(response_history)
        max_consecutive_correct = self._count_max_consecutive(response_history, True)
        max_consecutive_incorrect = self._count_max_consecutive(response_history, False)

        # Difficulty progression analysis
        difficulties = [d for _, d, _, _ in responses]
        difficulty_trend = 'increasing' if len(difficulties) > 1 and difficulties[-1] > difficulties[0] else \
                          'decreasing' if len(difficulties) > 1 and difficulties[-1] < difficulties[0] else \
                          'stable'

        # Test efficiency metrics
        total_information = sum(
            self.information(final_theta, d, a, g)
            for _, d, a, g in responses
        )
        avg_information = total_information / total_questions if total_questions > 0 else 0

        # Response time analysis
        time_analysis = {}
        if response_times and len(response_times) == total_questions:
            avg_time = np.mean(response_times)
            time_analysis = {
                'average_response_time': avg_time,
                'fastest_response': min(response_times),
                'slowest_response': max(response_times),
                'time_consistency': np.std(response_times)
            }

        # Compile report
        report = {
            'final_ability': final_theta,
            'final_tier': self.theta_to_tier(final_theta),
            'confidence_interval': confidence_interval,
            'final_sem': final_sem,
            'questions_answered': total_questions,
            'correct_answers': correct_count,
            'accuracy': accuracy,
            'test_efficiency': {
                'total_information': total_information,
                'average_information_per_item': avg_information,
                'relative_efficiency': avg_information / 2.0 if avg_information > 0 else 0  # Compared to optimal
            },
            'content_area_performance': content_performance,
            'response_patterns': {
                'max_consecutive_correct': max_consecutive_correct,
                'max_consecutive_incorrect': max_consecutive_incorrect,
                'final_pattern': consecutive_info,
                'difficulty_trend': difficulty_trend,
                'average_difficulty': np.mean(difficulties) if difficulties else 0
            },
            'theta_progression': {
                'initial_theta': self.theta_history[0] if self.theta_history else final_theta,
                'final_theta': final_theta,
                'total_change': final_theta - (self.theta_history[0] if self.theta_history else final_theta),
                'stability': np.var(self.theta_history[-5:]) if len(self.theta_history) >= 5 else None
            },
            'time_analysis': time_analysis,
            'test_purpose': self.test_purpose.value,
            'test_completed': questions_asked >= self.min_questions
        }

        # Add strengths and weaknesses summary - handle empty content_performance
        strengths = []
        weaknesses = []
        if content_performance:
            strengths = [area for area, data in content_performance.items()
                        if data.get('strength_level') == 'Strong']
            weaknesses = [area for area, data in content_performance.items()
                         if data.get('strength_level') == 'Weak']

        report['summary'] = {
            'strengths': strengths,
            'weaknesses': weaknesses,
            'recommended_focus_areas': weaknesses[:3] if weaknesses else [],
            'overall_performance': 'Advanced' if final_theta > 1.0 else \
                                 'Proficient' if final_theta > 0 else \
                                 'Developing' if final_theta > -1.0 else 'Beginning'
        }

        return report

    def calculate_theta_adjustment(self, current_theta: float,
                                  responses: List[Tuple[bool, float, float, float]],
                                  response_history: List[bool]) -> Tuple[float, Dict[str, Any]]:
        """Enhanced Newton-Raphson with all improvements"""
        if not responses:
            return current_theta, {'method': 'no_responses', 'change': 0.0}

        consecutive_info = self.detect_consecutive_responses(response_history)

        theta = current_theta
        iterations_used = 0
        total_change = 0.0
        converged = False

        logger.debug(f"Starting Newton-Raphson: initial_theta={current_theta:.4f}")

        for iteration in range(self.newton_raphson_iterations):
            iterations_used = iteration + 1
            likelihood_derivative = 0.0
            second_derivative = 0.0

            for is_correct, difficulty, discrimination, guessing in responses:
                p = self.cached_probability_correct(theta, difficulty, discrimination, guessing)
                p = max(min(p, 1.0 - self.PROBABILITY_EPSILON), self.PROBABILITY_EPSILON)
                q = 1 - p

                discrimination = max(0.1, min(discrimination, 3.0))

                if is_correct:
                    likelihood_derivative += discrimination * q / p
                else:
                    likelihood_derivative -= discrimination * p / q

                second_derivative -= discrimination ** 2 * p * q

            if abs(second_derivative) < self.MIN_SECOND_DERIVATIVE:
                logger.debug(f"Second derivative too small: {second_derivative:.2e}")
                break

            raw_delta_theta = -likelihood_derivative / second_derivative

            if abs(raw_delta_theta) < self.convergence_threshold:
                logger.debug(f"Converged after {iteration + 1} iterations")
                converged = True
                break

            # Use adaptive jump size from consecutive info
            if self.enable_consecutive_jumps and consecutive_info['apply_jump']:
                max_change = consecutive_info['jump_size']
                logger.debug(f"Using adaptive jump size: {max_change:.4f}")
            else:
                max_change = min(self.max_theta_change, self.MAX_SINGLE_STEP)

            delta_theta = raw_delta_theta
            if abs(delta_theta) > max_change:
                delta_theta = max_change if delta_theta > 0 else -max_change

            potential_total_change = abs(total_change + delta_theta)
            if potential_total_change > self.ABSOLUTE_MAX_TOTAL_CHANGE:
                remaining_budget = self.ABSOLUTE_MAX_TOTAL_CHANGE - abs(total_change)
                delta_theta = remaining_budget if delta_theta > 0 else -remaining_budget

                if abs(delta_theta) < self.convergence_threshold:
                    break

            new_theta = theta + delta_theta
            total_change += delta_theta

            bounded_theta = max(self.theta_bounds[0], min(self.theta_bounds[1], new_theta))
            if bounded_theta != new_theta:
                total_change = total_change - delta_theta + (bounded_theta - theta)

            theta = bounded_theta

            if abs(theta - (theta - delta_theta)) < self.convergence_threshold:
                converged = True
                break

        # Apply smoothing
        smoothing_alpha = self.exponential_smoothing_alpha * (0.8 if converged else 1.0)
        smoothed_theta = (smoothing_alpha * theta + (1 - smoothing_alpha) * current_theta)

        final_theta = max(self.theta_bounds[0], min(self.theta_bounds[1], smoothed_theta))

        final_change = final_theta - current_theta
        if abs(final_change) > self.ABSOLUTE_MAX_TOTAL_CHANGE:
            if final_change > 0:
                final_theta = current_theta + self.ABSOLUTE_MAX_TOTAL_CHANGE
            else:
                final_theta = current_theta - self.ABSOLUTE_MAX_TOTAL_CHANGE
            final_theta = max(self.theta_bounds[0], min(self.theta_bounds[1], final_theta))

        adjustment_info = {
            'method': 'newton_raphson_enhanced',
            'consecutive_info': consecutive_info,
            'theta_change': final_theta - current_theta,
            'iterations_used': iterations_used,
            'converged': converged,
            'adaptive_jump_size': consecutive_info.get('jump_size', 0.0),
            'smoothing_applied': True,
            'smoothing_alpha': smoothing_alpha,
            'total_change_during_nr': total_change,
            'bounds_hit': final_theta in self.theta_bounds
        }

        return final_theta, adjustment_info

    def update_theta(self, current_theta: float,
                    responses: List[Tuple[bool, float, float, float]],
                    response_history: List[bool] = None,
                    response_times: List[float] = None) -> Tuple[float, Dict[str, Any]]:
        """Main theta update method with all enhancements"""
        if response_history is None:
            response_history = [r[0] for r in responses]

        new_theta, info = self.robust_theta_update(
            current_theta, responses, response_history, response_times
        )

        # Update tracked current theta
        self.current_theta = new_theta

        logger.info(f"Theta updated: {current_theta:.3f} → {new_theta:.3f} (Δ={new_theta - current_theta:+.3f})")

        return new_theta, info

    def calculate_sem(self, theta: float,
                     questions_info: List[Tuple[float, float, float]]) -> float:
        """Calculate Standard Error of Measurement"""
        total_info = 0.0
        for difficulty, discrimination, guessing in questions_info:
            total_info += self.information(theta, difficulty, discrimination, guessing)

        if total_info <= 0:
            return 1.0

        return 1.0 / math.sqrt(total_info)

    def _apply_conservative_fairness_constraints(self, current_tier: str,
                                                response_history: List[bool],
                                                consecutive_info: Dict[str, Any]) -> str:
        """Apply conservative fairness constraints for tier adjustment"""

        if self.adaptive_config.tier_change_aggressive:
            min_questions = max(4, self.min_questions_before_tier_change // 2)
        else:
            min_questions = self.min_questions_before_tier_change

        if len(response_history) < min_questions:
            return current_tier

        # Check for tier promotion (only one tier at a time)
        if len(response_history) >= self.tier_promotion_window:
            recent_window = response_history[-self.tier_promotion_window:]
            correct_count = sum(recent_window)

            if correct_count >= self.tier_promotion_threshold:
                new_tier = self._adjust_tier_up(current_tier)  # Always single tier jump
                if new_tier != current_tier:
                    logger.info(f"TIER PROMOTION: {current_tier} → {new_tier} "
                              f"({correct_count}/{self.tier_promotion_window} correct)")
                    return new_tier

        # Check for tier demotion (only one tier at a time)
        if len(response_history) >= self.tier_demotion_window:
            recent_window = response_history[-self.tier_demotion_window:]
            correct_count = sum(recent_window)

            if correct_count <= self.tier_demotion_threshold:
                new_tier = self._adjust_tier_down(current_tier)  # Always single tier jump
                if new_tier != current_tier:
                    logger.info(f"TIER DEMOTION: {current_tier} → {new_tier} "
                              f"({correct_count}/{self.tier_demotion_window} correct)")
                    return new_tier

        return current_tier

    def _adjust_tier_up(self, tier: str) -> str:
        """Adjust tier up by exactly one level"""
        tier_order = ["C1", "C2", "C3", "C4"]
        try:
            current_index = tier_order.index(tier)
            # Only move up by 1 tier, not more
            new_index = min(current_index + 1, len(tier_order) - 1)
            return tier_order[new_index]
        except ValueError:
            logger.warning(f"Unknown tier: {tier}, defaulting to C1")
            return "C1"

    def _adjust_tier_down(self, tier: str) -> str:
        """Adjust tier down by exactly one level"""
        tier_order = ["C1", "C2", "C3", "C4"]
        try:
            current_index = tier_order.index(tier)
            # Only move down by 1 tier, not more
            new_index = max(current_index - 1, 0)
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

    def _count_max_consecutive(self, response_history: List[bool],
                              target_response: bool) -> int:
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

    def calculate_assessment_metrics(self, responses: List[Tuple[bool, float, float, float]],
                                    final_theta: float,
                                    response_history: List[bool] = None,
                                    question_details: List[Dict] = None) -> Dict:
        """
        Calculate final assessment metrics

        Args:
            responses: List of (is_correct, difficulty, discrimination, guessing) tuples
            final_theta: Final ability estimate
            response_history: Optional list of boolean responses
            question_details: Optional list of question dictionaries with topic/content_area info

        Returns:
            Complete assessment metrics dictionary

        Note: This method is backward compatible - question_details is optional.
        If not provided, content area analysis will be skipped.
        """
        # Call generate_diagnostic_report with optional question_details
        # If question_details is None, the report will skip content analysis
        return self.generate_diagnostic_report(
            final_theta,
            responses,
            response_history or [r[0] for r in responses],
            response_times=None,  # Add this for clarity
            question_details=question_details  # Will be None if not provided
        )

    @staticmethod
    def create_response_tuple(is_correct: bool, question: Dict) -> Tuple[bool, float, float, float]:
        """
        Helper method to create a response tuple from a question dictionary.

        Args:
            is_correct: Whether the answer was correct
            question: Question dictionary with IRT parameters

        Returns:
            Tuple of (is_correct, difficulty, discrimination, guessing)
        """
        return (
            is_correct,
            question.get('difficulty_b', 0.0),
            question.get('discrimination_a', 1.0),
            question.get('guessing_c', 0.25)
        )

    def clear_caches(self):
        """Clear performance optimization caches"""
        self._information_cache.clear()
        self._probability_cache.clear()
        self.cached_probability_correct.cache_clear()
        logger.info("Cleared all caches")

    def run_adaptive_assessment(self, initial_competence: str,
                               question_bank: List[Dict],
                               enable_response_times: bool = False) -> Dict:
        """
        Run a complete adaptive assessment session.

        This method demonstrates the complete workflow of:
        1. Initialize with competence level
        2. Select questions based on current theta
        3. Process responses and update theta
        4. Check stopping criteria
        5. Generate final report

        Args:
            initial_competence: Starting competence level ('beginner', 'intermediate', 'advanced', 'expert')
            question_bank: List of available questions with parameters
            enable_response_times: Whether to use response time in calculations

        Returns:
            Complete assessment report
        """
        # Step 1: Initialize assessment
        current_theta = self.initialize_assessment(initial_competence)

        # Initialize tracking variables
        responses = []
        response_history = []
        response_times = [] if enable_response_times else None
        available_questions = question_bank.copy()
        questions_answered = 0
        question_details = []  # Track question details for content analysis

        logger.info(f"Starting adaptive assessment with {len(available_questions)} questions in bank")

        # Step 2: Main assessment loop
        while questions_answered < self.max_questions:
            # Select next question based on CURRENT theta
            next_question = self.select_next_question(
                theta=current_theta,  # Always use current theta
                available_questions=available_questions,
                response_history=response_history
            )

            if not next_question:
                logger.warning("No more suitable questions available")
                break

            # Remove selected question from available pool
            available_questions.remove(next_question)

            # Store question details for content analysis
            question_details.append(next_question)

            # Simulate getting response (in real implementation, this would come from user)
            # For demonstration, we'll simulate based on probability
            prob_correct = self.probability_correct(
                current_theta,
                next_question['difficulty_b'],
                next_question['discrimination_a'],
                next_question.get('guessing_c', 0.25)
            )

            # Simulate response (in production, this would be actual user response)
            is_correct = random.random() < prob_correct

            # Add to response tracking
            response_tuple = (
                is_correct,
                next_question['difficulty_b'],
                next_question['discrimination_a'],
                next_question.get('guessing_c', 0.25)
            )
            responses.append(response_tuple)
            response_history.append(is_correct)

            # Simulate response time if enabled
            if enable_response_times:
                # Simulate response time based on difficulty distance
                base_time = 15.0
                difficulty_distance = abs(current_theta - next_question['difficulty_b'])
                simulated_time = base_time + random.uniform(-5, 5) + difficulty_distance * 3
                response_times.append(simulated_time)

            questions_answered += 1

            # Step 3: Update theta based on response
            current_theta, update_info = self.update_theta(
                current_theta=current_theta,
                responses=[response_tuple],  # Can be just the latest or all cumulative
                response_history=response_history,
                response_times=response_times[-1:] if response_times else None
            )

            logger.debug(f"Question {questions_answered}: "
                        f"Correct={is_correct}, "
                        f"New theta={current_theta:.3f}, "
                        f"Method={update_info.get('method', 'unknown')}")

            # Step 4: Check stopping criteria
            current_sem = self.calculate_sem(
                current_theta,
                [(r[1], r[2], r[3]) for r in responses]
            )

            should_stop, confidence = self.should_stop_with_confidence(
                sem=current_sem,
                questions_asked=questions_answered,
                response_history=response_history
            )

            if should_stop and questions_answered >= self.min_questions:
                logger.info(f"Stopping assessment: questions={questions_answered}, "
                          f"SEM={current_sem:.3f}, confidence={confidence:.2f}")
                break

        # Step 5: Generate final report with question details
        final_report = self.generate_diagnostic_report(
            final_theta=current_theta,
            responses=responses,
            response_history=response_history,
            response_times=response_times,
            question_details=question_details  # Pass question details for content analysis
        )

        # Add assessment metadata
        final_report['assessment_metadata'] = {
            'initial_competence': initial_competence,
            'initial_theta': self.theta_history[0] if self.theta_history else current_theta,
            'question_bank_size': len(question_bank),
            'questions_remaining': len(available_questions),
            'test_purpose': self.test_purpose.value,
            'response_times_enabled': enable_response_times
        }

        logger.info(f"Assessment completed: Final theta={current_theta:.3f}, "
                   f"Questions={questions_answered}, "
                   f"Final tier={final_report['final_tier']}")

        return final_report


# Convenience factory functions for easy initialization
def create_irt_engine(config=None, test_purpose=TestPurpose.DIAGNOSTIC):
    """
    Factory function to create an IRT engine with flexible config handling.

    Args:
        config: Can be:
            - None (uses defaults)
            - A dictionary with 'irt_config' and 'tier_config' keys
            - A config object from your existing system
            - A dictionary of just IRT parameters (tier_config will use defaults)
        test_purpose: TestPurpose enum (SCREENING, DIAGNOSTIC, PLACEMENT)

    Returns:
        Configured IRTEngine instance

    Examples:
        # Use defaults
        engine = create_irt_engine()

        # Use your existing config
        from config import get_config
        engine = create_irt_engine(get_config())

        # Use custom config dict
        engine = create_irt_engine({
            'irt_config': {...},
            'tier_config': {...}
        })
    """
    return IRTEngine(config=config, test_purpose=test_purpose)


def create_simple_irt_engine(config=None):
    """
    Create a simplified IRT engine that works with minimal configuration.
    Content balancing is disabled to avoid any issues with missing question details.

    This is the safest option if you're getting errors and don't want to change other files.

    Returns:
        IRTEngine instance with content balancing disabled

    Example:
        from irt_engine import create_simple_irt_engine

        engine = create_simple_irt_engine()
        metrics = engine.calculate_assessment_metrics(responses, final_theta)
        # No errors, no changes needed to other files!
    """
    engine = IRTEngine(config=config, test_purpose=TestPurpose.DIAGNOSTIC)
    engine.adaptive_config.enable_content_balancing = False
    return engine


# Helper function for default configuration
def get_default_config():
    """Default configuration as a simple dictionary"""
    return {
        "irt_config": {
            "target_sem": 0.3,
            "max_questions": 30,
            "min_questions": 10,
            "history_window": 5,
            "max_theta_change": 0.5,
            "theta_jump": 0.8,
            "consecutive_same_responses": 3,
            "theta_bounds": [-3.0, 3.0],
            "newton_raphson_iterations": 10,
            "convergence_threshold": 0.001,
            "exponential_smoothing_alpha": 0.7,
            "enable_consecutive_jumps": True,
            "tier_promotion_window": 8,
            "tier_promotion_threshold": 6,
            "tier_demotion_window": 8,
            "tier_demotion_threshold": 2,
            "min_questions_before_tier_change": 8
        },
        "tier_config": {
            "theta_ranges": {
                "C1": [-3.0, -1.0],
                "C2": [-1.0, 0.0],
                "C3": [0.0, 1.0],
                "C4": [1.0, 3.0]
            },
            "discrimination_ranges": {
                "C1": [0.5, 1.5],
                "C2": [0.7, 1.7],
                "C3": [0.8, 2.0],
                "C4": [1.0, 2.5]
            },
            "difficulty_ranges": {
                "C1": [-2.0, 0.0],
                "C2": [-1.0, 1.0],
                "C3": [0.0, 2.0],
                "C4": [1.0, 3.0]
            },
            "initial_theta_map": {
                "beginner": -1.5,
                "intermediate": 0.0,
                "advanced": 1.5,
                "expert": 2.0
            }
        }
    }


# Backward compatibility wrapper
def get_config():
    """Legacy config loader - returns object-like interface"""
    default_config = get_default_config()
    return {
        "get_irt_config": lambda: default_config["irt_config"],
        "get_tier_config": lambda: default_config["tier_config"]
    }


# Example usage and testing
# if __name__ == "__main__":
#     # Set up logging
#     logging.basicConfig(level=logging.INFO)
#
#     # Method 1: Using default config
#     engine1 = IRTEngine()
#     print("Engine 1 initialized with default config")
#
#     # Method 2: Using a dictionary config
#     custom_config = {
#         "irt_config": {
#             "target_sem": 0.25,
#             "max_questions": 40,
#             "min_questions": 15,
#             "history_window": 5,
#             "max_theta_change": 0.5,
#             "theta_jump": 0.8,
#             "consecutive_same_responses": 3,
#             "theta_bounds": [-3.0, 3.0],
#             "newton_raphson_iterations": 10,
#             "convergence_threshold": 0.001,
#             "exponential_smoothing_alpha": 0.7,
#             "enable_consecutive_jumps": True,
#             "tier_promotion_window": 8,
#             "tier_promotion_threshold": 6,
#             "tier_demotion_window": 8,
#             "tier_demotion_threshold": 2,
#             "min_questions_before_tier_change": 8
#         },
#         "tier_config": {
#             "theta_ranges": {
#                 "C1": [-3.0, -1.0],
#                 "C2": [-1.0, 0.0],
#                 "C3": [0.0, 1.0],
#                 "C4": [1.0, 3.0]
#             },
#             "discrimination_ranges": {
#                 "C1": [0.5, 1.5],
#                 "C2": [0.7, 1.7],
#                 "C3": [0.8, 2.0],
#                 "C4": [1.0, 2.5]
#             },
#             "difficulty_ranges": {
#                 "C1": [-2.0, 0.0],
#                 "C2": [-1.0, 1.0],
#                 "C3": [0.0, 2.0],
#                 "C4": [1.0, 3.0]
#             },
#             "initial_theta_map": {
#                 "beginner": -1.5,
#                 "intermediate": 0.0,
#                 "advanced": 1.5,
#                 "expert": 2.0
#             }
#         }
#     }
#     engine2 = IRTEngine(config=custom_config, test_purpose=TestPurpose.DIAGNOSTIC)
#     print("Engine 2 initialized with custom dictionary config")
#
#     # Method 3: Using the legacy object-style config
#     legacy_config = get_config()  # Returns object with get_irt_config() method
#     engine3 = IRTEngine(config=legacy_config)
#     print("Engine 3 initialized with legacy config format")
#
#     # Method 4: If you have an existing config module (common case)
#     # Assuming your config.py returns something like this:
#     # config = get_config()  # Your existing config loader
#     # You can wrap it:
#     try:
#         from config import get_config as original_get_config
#         user_config = original_get_config()
#
#         # Convert to the expected format
#         if hasattr(user_config, 'get_irt_config'):
#             # It's already in the right format
#             engine4 = IRTEngine(config=user_config)
#         else:
#             # Wrap it in the expected format
#             wrapped_config = {
#                 'irt_config': user_config.get('irt_config', get_default_config()['irt_config']),
#                 'tier_config': user_config.get('tier_config', get_default_config()['tier_config'])
#             }
#             engine4 = IRTEngine(config=wrapped_config)
#         print("Engine 4 initialized with existing config module")
#     except ImportError:
#         print("No existing config module found, skipping Method 4")
#
#     # Create sample question bank
#     sample_question_bank = [
#         {"id": f"q{i}",
#          "difficulty_b": -2.0 + (i * 0.2),
#          "discrimination_a": 1.0 + (i * 0.05),
#          "guessing_c": 0.25,
#          "content_area": f"area_{i % 3}"}
#         for i in range(50)
#     ]
#
#     # Run a simulated assessment with engine2
#     # Example: Full assessment with content analysis
#     print("\n" + "="*50)
#     print("Running full assessment with content analysis...")
#     print("="*50)
#
#     report = engine2.run_adaptive_assessment(
#         initial_competence="intermediate",
#         question_bank=sample_question_bank,
#         enable_response_times=True
#     )
#
#     # Print summary
#     print("\n=== Assessment Report Summary ===")
#     print(f"Final Ability: {report['final_ability']:.3f}")
#     print(f"Final Tier: {report['final_tier']}")
#     print(f"Questions Answered: {report['questions_answered']}")
#     print(f"Accuracy: {report['accuracy']:.2%}")
#     print(f"Overall Performance: {report['summary']['overall_performance']}")
#
#     # Example: Simpler usage when content analysis is not needed
#     print("\n" + "="*50)
#     print("Example: Simple assessment without content analysis")
#     print("="*50)
#
#     # Disable content balancing for simpler usage
#     simple_engine = IRTEngine(test_purpose=TestPurpose.SCREENING)
#     simple_engine.adaptive_config.enable_content_balancing = False
#
#     # Run assessment
#     simple_report = simple_engine.run_adaptive_assessment(
#         initial_competence="beginner",
#         question_bank=sample_question_bank[:20],  # Smaller bank for demo
#         enable_response_times=False
#     )
#
#     print(f"Simple Assessment Complete:")
#     print(f"  Final Ability: {simple_report['final_ability']:.3f}")
#     print(f"  Questions: {simple_report['questions_answered']}")
#     print(f"  Accuracy: {simple_report['accuracy']:.2%}")
#
#     print("\n" + "="*50)
#     print("IRT Engine Test Complete!")
#     print("="*50)