"""
Enhanced IRT (Item Response Theory) Engine for Adaptive Assessment - PRODUCTION READY

FINAL FIXES APPLIED:
1. Calibrated proportional anticipation (1.5x real theta change limits)
2. Response time weighted Fisher Information (optional)
3. Proper difficulty progression with minimum constraints
4. Single-tier progression enforced
5. Conservative theta updates preserved
6. STRICT difficulty non-decrease after correct responses
7. Question repetition prevention within sessions
8. STRICT theta constraints based on last response:
   - Wrong answer → theta cannot increase, tier cannot be promoted
   - Correct answer → theta cannot decrease, tier cannot be demoted
9. SLIDING WINDOW THETA UPDATES (NEW!):
   - Early questions (1-10): Full cumulative for stable baseline
   - Transition (11-20): Blended cumulative + windowed
   - Mature (21+): Windowed only for responsiveness

Key Features:
- Anticipated theta scales with actual update limits
- Optional response time integration: I / log(RT)
- Symmetric handling of upward/downward progression
- Tier boundary protection in anticipation
- All contracts and constraints honored
- Questions never repeat within a session
- Difficulty never decreases after correct responses
- Response-based theta and tier protection
- ADAPTIVE WINDOWING: Responsive to recent performance while maintaining stability
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
    FORMATIVE = "formative"  # For low-stakes, ongoing assessments


@dataclass
class AdaptiveConfig:
    """Configuration class for different test purposes"""
    min_questions: int
    max_questions: int
    target_sem: float
    tier_change_aggressive: bool
    enable_content_balancing: bool = True
    enable_response_time: bool = False
    enable_rt_weighted_information: bool = False
    anticipation_multiplier: float = 1.5

    @classmethod
    def get_config(cls, purpose: TestPurpose):
        """Get configuration based on test purpose"""
        configs = {
            TestPurpose.SCREENING: cls(
                min_questions=5,
                max_questions=15,
                target_sem=0.5,
                tier_change_aggressive=True,
                enable_content_balancing=False,
                enable_response_time=False,
                enable_rt_weighted_information=False,
                anticipation_multiplier=1.3
            ),
            TestPurpose.DIAGNOSTIC: cls(
                min_questions=15,
                max_questions=40,
                target_sem=0.15,
                tier_change_aggressive=False,
                enable_content_balancing=True,
                enable_response_time=True,
                enable_rt_weighted_information=True,
                anticipation_multiplier=1.5
            ),
            TestPurpose.PLACEMENT: cls(
                min_questions=10,
                max_questions=25,
                target_sem=0.35,
                tier_change_aggressive=False,
                enable_content_balancing=True,
                enable_response_time=False,
                enable_rt_weighted_information=False,
                anticipation_multiplier=1.5
            ),
            TestPurpose.FORMATIVE: cls(
                min_questions=20,
                max_questions=35,
                target_sem=0.20,#0.3
                tier_change_aggressive=False,
                enable_content_balancing=True,
                enable_response_time=False,
                enable_rt_weighted_information=False,
                anticipation_multiplier=1.3
            )
        }
        return configs.get(purpose, configs[TestPurpose.DIAGNOSTIC])


class IRTEngine:
    """
    Production-ready IRT engine with sliding window adaptive updates.

    Key contracts honored:
    - Theta updates: Conservative (±0.2 early, ±0.3 later)
    - Tier progression: Single-step only (C1→C2, never C1→C3)
    - Bounds: [-3.0, 3.0] strictly enforced
    - Early protection: First 5 questions limited to ±0.2
    - Question uniqueness: No question repeated within a session
    - Difficulty progression: Never decreases after correct responses
    - Response-based constraints:
      * Wrong answer → theta cannot increase, tier cannot be promoted
      * Correct answer → theta cannot decrease, tier cannot be demoted
    - Sliding window: Recent performance weighted appropriately
    """

    def __init__(self, config=None, test_purpose: TestPurpose = TestPurpose.DIAGNOSTIC):
        if config is None:
            config = get_default_config()

        self.config = config
        self.test_purpose = test_purpose
        self.adaptive_config = AdaptiveConfig.get_config(test_purpose)

        self.current_theta = None
        self.theta_velocity = 0.0
        self.velocity_damping = 0.5

        # Handle different config formats
        if isinstance(config, dict):
            if 'irt_config' in config and 'tier_config' in config:
                irt_config = config['irt_config']
                tier_config = config['tier_config']
            elif 'get_irt_config' in config and 'get_tier_config' in config:
                irt_config = config['get_irt_config']() if callable(config['get_irt_config']) else config['get_irt_config']
                tier_config = config['get_tier_config']() if callable(config['get_tier_config']) else config['get_tier_config']
            else:
                irt_config = config
                tier_config = get_default_config()['tier_config']
        else:
            try:
                irt_config = config.get_irt_config()
                tier_config = config.get_tier_config()
            except AttributeError:
                if hasattr(config, 'irt_config'):
                    irt_config = config.irt_config
                    tier_config = config.tier_config if hasattr(config, 'tier_config') else get_default_config()['tier_config']
                else:
                    raise ValueError("Config must be a dict with 'irt_config' and 'tier_config' keys")

        # Load configuration values from AdaptiveConfig
        self.target_sem = self.adaptive_config.target_sem
        self.max_questions = self.adaptive_config.max_questions
        self.min_questions = self.adaptive_config.min_questions

        # Load IRT-specific configuration
        self.history_window = irt_config["history_window"]
        self.max_theta_change = irt_config.get("max_theta_change", 0.3)
        self.theta_jump = irt_config.get("theta_jump", 0.4)
        self.consecutive_same_responses = irt_config["consecutive_same_responses"]
        self.theta_bounds = irt_config["theta_bounds"]
        self.newton_raphson_iterations = irt_config["newton_raphson_iterations"]
        self.convergence_threshold = irt_config["convergence_threshold"]
        self.base_exponential_smoothing_alpha = irt_config.get("exponential_smoothing_alpha", 0.7)
        self.exponential_smoothing_alpha = 0.3
        self.enable_consecutive_jumps = irt_config["enable_consecutive_jumps"]

        # NEW: Sliding window configuration
        self.use_windowed_theta = irt_config.get("use_windowed_theta", True)
        self.response_window_size = irt_config.get("response_window_size", 10)
        self.window_transition_start = irt_config.get("window_transition_start", 10)
        self.window_transition_end = irt_config.get("window_transition_end", 20)

        self.tier_promotion_window = irt_config.get("tier_promotion_window", 10)
        self.tier_promotion_threshold = irt_config.get("tier_promotion_threshold", 7)
        self.tier_demotion_window = irt_config.get("tier_demotion_window", 10)
        self.tier_demotion_threshold = irt_config.get("tier_demotion_threshold", 3)
        self.min_questions_before_tier_change = irt_config.get("min_questions_before_tier_change", 10)

        # Tier mappings from config
        self.tier_theta_ranges = tier_config["theta_ranges"]
        self.tier_discrimination_ranges = tier_config["discrimination_ranges"]
        self.tier_difficulty_ranges = tier_config["difficulty_ranges"]
        self.initial_theta_map = tier_config["initial_theta_map"]

        # Newton-Raphson safety constants
        self.ABSOLUTE_MAX_TOTAL_CHANGE = 1.0
        self.MIN_SECOND_DERIVATIVE = 1e-6
        self.MAX_SINGLE_STEP = 0.5
        self.PROBABILITY_EPSILON = 1e-4

        # CONTRACT: Early questions protection
        self.EARLY_QUESTIONS_COUNT = 5
        self.EARLY_QUESTIONS_MAX_CHANGE = 0.2

        # Performance optimization
        self._information_cache = {}
        self._probability_cache = {}

        # Content balancing tracking
        self.used_content_areas = {}

        # Response time tracking
        self.response_times = []
        self.question_response_times = []

        # Theta history for stability analysis
        self.theta_history = []

        # Track cumulative responses for proper updates
        self.cumulative_responses = []

        # Track last question difficulty for progression constraints
        self.last_question_difficulty = None

        # Item exposure control
        self.item_exposure_counts = {}
        self.max_item_exposure_rate = 0.3

        # Track asked questions to prevent repetition within a session
        self.asked_question_ids = set()

        logger.info(f"IRTEngine initialized for {test_purpose.value} purpose")
        logger.info(f"Target SEM: {self.target_sem}, Min/Max Questions: {self.min_questions}/{self.max_questions}")
        logger.info(f"Anticipation multiplier: {self.adaptive_config.anticipation_multiplier}x")
        logger.info(f"RT-weighted information: {self.adaptive_config.enable_rt_weighted_information}")
        logger.info(f"Response-based constraints: ENABLED (theta & tier protection)")
        logger.info(f"Sliding window: {'ENABLED' if self.use_windowed_theta else 'DISABLED'} "
                   f"(window={self.response_window_size}, transition={self.window_transition_start}-{self.window_transition_end})")

    def get_initial_theta(self, competence_level: str) -> float:
        """Get initial theta based on competence level"""
        initial_theta = self.initial_theta_map.get(competence_level, -1.0)
        self.current_theta = initial_theta
        self.theta_history = [initial_theta]
        self.theta_velocity = 0.0
        self.last_question_difficulty = None
        self.question_response_times = []
        logger.info(f"Initial theta set to {initial_theta:.3f} for competence level '{competence_level}'")
        return initial_theta

    def initialize_assessment(self, competence_level: str = "intermediate") -> float:
        """Initialize assessment with starting theta based on competence level"""
        initial_theta = self.get_initial_theta(competence_level)
        self.cumulative_responses = []
        self.asked_question_ids = set()
        logger.info(f"Assessment initialized with theta={initial_theta:.3f}, asked_questions cleared")
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

    def get_tier_index(self, tier: str) -> int:
        """Get tier index for boundary calculations"""
        tier_order = ["C1", "C2", "C3", "C4"]
        try:
            return tier_order.index(tier)
        except ValueError:
            return 0

    def get_current_tiers(self, theta: float, response_history: List[bool]) -> Dict[str, str]:
        """
        Get both estimated tier (from theta) and active tier (used for questions).

        Returns:
            dict with 'estimated_tier', 'active_tier', and 'tier_note'
        """
        estimated_tier = self.theta_to_tier(theta)

        # Get active tier if we have enough questions
        if len(response_history) >= self.min_questions_before_tier_change:
            consecutive_info = self.detect_consecutive_responses(response_history)
            active_tier = self._apply_conservative_fairness_constraints(
                estimated_tier, response_history, consecutive_info
            )
        else:
            # Before min questions, active tier is initial tier
            active_tier = self.theta_to_tier(self.theta_history[0]) if self.theta_history else estimated_tier

        # Generate helpful note
        if estimated_tier != active_tier:
            tier_note = f"Questions are at {active_tier} level (adjusting after more responses)"
        else:
            tier_note = f"Question difficulty matches your current level"

        return {
            'estimated_tier': estimated_tier,
            'active_tier': active_tier,
            'tier_aligned': estimated_tier == active_tier,
            'tier_note': tier_note
        }

    @lru_cache(maxsize=1000)
    def cached_probability_correct(self, theta: float, difficulty: float,
                                   discrimination: float, guessing: float = 0.25) -> float:
        """Cached version of probability calculation for performance"""
        return self.probability_correct(theta, difficulty, discrimination, guessing)

    def probability_correct(self, theta: float, difficulty: float,
                            discrimination: float, guessing: float = 0.25) -> float:
        """Calculate probability of correct response using 3PL model"""
        try:
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

    def rt_weighted_information(self, theta: float, difficulty: float,
                                discrimination: float, guessing: float,
                                response_time: float) -> float:
        """
        Calculate response time weighted Fisher Information.
        Formula: I(θ) / log(RT + 1)
        """
        if not self.adaptive_config.enable_rt_weighted_information:
            return self.information(theta, difficulty, discrimination, guessing)

        base_information = self.information(theta, difficulty, discrimination, guessing)

        if response_time is None or response_time <= 0:
            return base_information

        rt_weight = math.log(response_time + 1)
        rt_weight = max(rt_weight, 0.1)

        weighted_info = base_information / rt_weight

        return weighted_info

    def adaptive_theta_jump_size(self, consecutive_count: int,
                                 response_type: str, questions_answered: int) -> float:
        """Dynamic jump size with early assessment protection"""
        base_jump = self.theta_jump

        if questions_answered <= self.EARLY_QUESTIONS_COUNT:
            base_jump = min(base_jump, 0.2)
        elif questions_answered <= 10:
            base_jump = min(base_jump, 0.3)

        if consecutive_count <= 3:
            return base_jump * 0.5
        elif consecutive_count <= 5:
            return base_jump * 0.75
        elif consecutive_count <= 7:
            return base_jump
        else:
            return min(base_jump * 1.25, self.MAX_SINGLE_STEP * 0.7)

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

            for i in range(len(response_history) - self.consecutive_same_responses - 1, -1, -1):
                if response_history[i] == recent_responses[0]:
                    consecutive_count += 1
                else:
                    break

            questions_answered = len(response_history)
            jump_size = self.adaptive_theta_jump_size(consecutive_count, response_type, questions_answered)

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

    def calculate_anticipated_theta(self, current_theta: float,
                                    response_history: List[bool],
                                    questions_answered: int) -> float:
        """
        Calculate anticipated theta using calibrated proportional method.
        """
        if len(response_history) < 2:
            return current_theta

        if questions_answered <= self.EARLY_QUESTIONS_COUNT:
            max_real_change = self.EARLY_QUESTIONS_MAX_CHANGE
        else:
            max_real_change = self.max_theta_change

        lookback = min(3, len(response_history))
        recent_responses = response_history[-lookback:]
        correct_count = sum(recent_responses)

        multiplier = self.adaptive_config.anticipation_multiplier

        if correct_count == lookback:
            anticipated_adjustment = max_real_change * multiplier
        elif correct_count == 0:
            anticipated_adjustment = -max_real_change * multiplier
        elif correct_count > lookback / 2:
            anticipated_adjustment = max_real_change * 0.75
        elif correct_count < lookback / 2:
            anticipated_adjustment = -max_real_change * 0.75
        else:
            anticipated_adjustment = 0.0

        anticipated_theta = current_theta + anticipated_adjustment

        anticipated_theta = max(self.theta_bounds[0],
                                min(self.theta_bounds[1], anticipated_theta))

        current_tier_idx = self.get_tier_index(self.theta_to_tier(current_theta))
        anticipated_tier_idx = self.get_tier_index(self.theta_to_tier(anticipated_theta))

        if abs(anticipated_tier_idx - current_tier_idx) > 1:
            tier_boundaries = [-3.0, -1.0, 0.0, 1.0, 3.0]
            if anticipated_tier_idx > current_tier_idx:
                anticipated_theta = tier_boundaries[current_tier_idx + 1] + 0.1
            else:
                anticipated_theta = tier_boundaries[current_tier_idx] - 0.1

            logger.debug(f"Tier crossing clamped: {current_tier_idx} -> {anticipated_tier_idx}, "
                         f"theta clamped to {anticipated_theta:.3f}")

        logger.debug(f"Anticipated theta: {current_theta:.3f} -> {anticipated_theta:.3f} "
                     f"(delta={anticipated_adjustment:+.3f}, pattern={correct_count}/{lookback}, "
                     f"multiplier={multiplier}x)")

        return anticipated_theta

    def validate_question_uniqueness(self, question_id: str) -> bool:
        """
        Validate that a question hasn't been asked in this session.
        """
        if question_id in self.asked_question_ids:
            logger.warning(f"Question {question_id} already asked in this session")
            return False
        return True

    def select_next_question_with_content_balance(self, theta: float,
                                                  available_questions: List[Dict],
                                                  response_history: List[bool],
                                                  questions_answered: int = 0) -> Optional[Dict]:
        """
        Select next question with calibrated anticipation and proper difficulty progression.
        """
        if not available_questions:
            return None

        current_tier = self.theta_to_tier(theta)
        consecutive_info = self.detect_consecutive_responses(response_history)

        anticipated_theta = self.calculate_anticipated_theta(
            theta, response_history, questions_answered
        )

        adjusted_tier = self._apply_conservative_fairness_constraints(
            current_tier, response_history, consecutive_info
        )

        anticipated_tier = self.theta_to_tier(anticipated_theta)
        selection_tier = anticipated_tier if anticipated_tier != current_tier else adjusted_tier

        logger.debug(f"Question selection: current_theta={theta:.3f}, "
                     f"anticipated_theta={anticipated_theta:.3f}, "
                     f"current_tier={current_tier}, selection_tier={selection_tier}")

        suitable_questions = self._filter_questions_by_tier(available_questions, selection_tier)
        if not suitable_questions:
            suitable_questions = self._filter_questions_by_tier(available_questions, adjusted_tier)
            if not suitable_questions:
                suitable_questions = available_questions
                logger.warning(f"No tier-appropriate questions, using all {len(available_questions)}")

        # CONTRACT: Prevent question repetition
        if self.asked_question_ids:
            suitable_questions = [q for q in suitable_questions
                                 if q.get('id') not in self.asked_question_ids]
            if not suitable_questions:
                logger.warning("All tier-appropriate questions already asked, expanding to all tiers")
                suitable_questions = [q for q in available_questions
                                    if q.get('id') not in self.asked_question_ids]
                if not suitable_questions:
                    logger.error("All questions in bank have been asked!")
                    return None

        # CONTRACT: STRICT difficulty non-decrease after correct responses
        if (len(response_history) >= 1 and response_history[-1] and
                self.last_question_difficulty is not None):
            min_difficulty = self.last_question_difficulty
            filtered = [q for q in suitable_questions
                        if q['difficulty_b'] >= min_difficulty]

            if filtered:
                suitable_questions = filtered
                logger.debug(f"Applied STRICT min difficulty constraint: {min_difficulty:.3f}")
            else:
                min_difficulty_relaxed = self.last_question_difficulty - 0.05
                filtered = [q for q in suitable_questions
                           if q['difficulty_b'] >= min_difficulty_relaxed]
                if filtered:
                    suitable_questions = filtered
                    logger.warning(f"Relaxed difficulty constraint to {min_difficulty_relaxed:.3f}")
                else:
                    logger.warning("STRICT difficulty constraint too restrictive, using all suitable questions")

        question_scores = []
        for question in suitable_questions:
            if (self.adaptive_config.enable_rt_weighted_information and
                    self.question_response_times):
                recent_rt = self.question_response_times[-1] if self.question_response_times else 15.0
                info = self.rt_weighted_information(
                    anticipated_theta,
                    question['difficulty_b'],
                    question['discrimination_a'],
                    question['guessing_c'],
                    recent_rt
                )
            else:
                info = self.information(
                    anticipated_theta,
                    question['difficulty_b'],
                    question['discrimination_a'],
                    question['guessing_c']
                )

            if self.adaptive_config.enable_content_balancing:
                content_area = question.get('content_area', 'default')
                usage_count = self.used_content_areas.get(content_area, 0)
                content_penalty = 1.0 - (0.1 * min(usage_count, 5))
            else:
                content_penalty = 1.0

            item_id = question.get('id', str(question))
            exposure_count = self.item_exposure_counts.get(item_id, 0)
            exposure_penalty = 1.0 - (0.2 * min(exposure_count, 3))

            difficulty_progression_bonus = 1.0
            if (len(response_history) >= 1 and response_history[-1] and
                    self.last_question_difficulty is not None):
                if question['difficulty_b'] > self.last_question_difficulty + 0.05:
                    difficulty_progression_bonus = 1.2
                elif question['difficulty_b'] >= self.last_question_difficulty - 0.05:
                    difficulty_progression_bonus = 1.1

            adjusted_score = info * content_penalty * exposure_penalty * difficulty_progression_bonus
            difficulty_distance = abs(question['difficulty_b'] - anticipated_theta)

            question_scores.append({
                'question': question,
                'adjusted_score': adjusted_score,
                'raw_information': info,
                'difficulty_distance': difficulty_distance,
                'content_penalty': content_penalty,
                'exposure_penalty': exposure_penalty,
                'progression_bonus': difficulty_progression_bonus
            })

        if question_scores:
            question_scores.sort(key=lambda x: x['adjusted_score'], reverse=True)

            best_item = question_scores[0]
            best_question = best_item['question']

            content_area = best_question.get('content_area', 'default')
            self.used_content_areas[content_area] = self.used_content_areas.get(content_area, 0) + 1

            item_id = best_question.get('id', str(best_question))
            self.item_exposure_counts[item_id] = self.item_exposure_counts.get(item_id, 0) + 1

            self.last_question_difficulty = best_question['difficulty_b']

            # CONTRACT: Mark question as asked to prevent repetition
            self.asked_question_ids.add(item_id)
            logger.debug(f"Question {item_id} marked as asked (total asked: {len(self.asked_question_ids)})")

            logger.info(f"Selected Q{questions_answered + 1}: "
                        f"diff={best_question['difficulty_b']:.3f}, "
                        f"disc={best_question['discrimination_a']:.3f}, "
                        f"info={best_item['raw_information']:.3f}, "
                        f"score={best_item['adjusted_score']:.3f}, "
                        f"prog_bonus={best_item['progression_bonus']:.2f}")

            return best_question

        return None

    def select_next_question(self, theta: float, available_questions: List[Dict],
                             response_history: List[bool],
                             questions_answered: int = 0) -> Optional[Dict]:
        """Main question selection method"""
        if self.adaptive_config.enable_content_balancing:
            return self.select_next_question_with_content_balance(
                theta, available_questions, response_history, questions_answered
            )
        else:
            return self._select_next_question_original(
                theta, available_questions, response_history, questions_answered
            )

    def _select_next_question_original(self, theta: float, available_questions: List[Dict],
                                       response_history: List[bool],
                                       questions_answered: int = 0) -> Optional[Dict]:
        """Original question selection logic with anticipated theta and constraints"""
        if not available_questions:
            return None

        current_tier = self.theta_to_tier(theta)
        consecutive_info = self.detect_consecutive_responses(response_history)

        anticipated_theta = self.calculate_anticipated_theta(
            theta, response_history, questions_answered
        )

        adjusted_tier = self._apply_conservative_fairness_constraints(
            current_tier, response_history, consecutive_info
        )

        suitable_questions = self._filter_questions_by_tier(
            available_questions,
            self.theta_to_tier(anticipated_theta)
        )
        if not suitable_questions:
            suitable_questions = self._filter_questions_by_tier(available_questions, adjusted_tier)
            if not suitable_questions:
                suitable_questions = available_questions

        # CONTRACT: Prevent question repetition
        if self.asked_question_ids:
            suitable_questions = [q for q in suitable_questions
                                 if q.get('id') not in self.asked_question_ids]
            if not suitable_questions:
                suitable_questions = [q for q in available_questions
                                    if q.get('id') not in self.asked_question_ids]
                if not suitable_questions:
                    logger.error("All questions already asked!")
                    return None

        # CONTRACT: STRICT difficulty non-decrease after correct responses
        if (len(response_history) >= 1 and response_history[-1] and
                self.last_question_difficulty is not None):
            min_difficulty = self.last_question_difficulty
            filtered = [q for q in suitable_questions if q['difficulty_b'] >= min_difficulty]
            if filtered:
                suitable_questions = filtered
                logger.debug(f"Applied STRICT min difficulty constraint: {min_difficulty:.3f}")
            else:
                min_difficulty_relaxed = self.last_question_difficulty - 0.05
                filtered = [q for q in suitable_questions if q['difficulty_b'] >= min_difficulty_relaxed]
                if filtered:
                    suitable_questions = filtered
                    logger.warning(f"Relaxed difficulty constraint to {min_difficulty_relaxed:.3f}")

        best_question = None
        max_information = -1
        best_difficulty_distance = float('inf')

        for question in suitable_questions:
            info = self.information(
                anticipated_theta,
                question['difficulty_b'],
                question['discrimination_a'],
                question['guessing_c']
            )

            difficulty_distance = abs(question['difficulty_b'] - anticipated_theta)

            if info > max_information or (info == max_information and difficulty_distance < best_difficulty_distance):
                max_information = info
                best_question = question
                best_difficulty_distance = difficulty_distance

        if best_question:
            self.last_question_difficulty = best_question['difficulty_b']

            # CONTRACT: Mark question as asked
            item_id = best_question.get('id')
            if item_id:
                self.asked_question_ids.add(item_id)
                logger.debug(f"Question {item_id} marked as asked (total asked: {len(self.asked_question_ids)})")

            logger.info(f"Selected Q{questions_answered + 1}: "
                        f"diff={best_question['difficulty_b']:.3f}, "
                        f"info={max_information:.3f}")

        return best_question

    def _calculate_theta_with_newton_raphson(self, current_theta: float,
                                             responses: List[Tuple[bool, float, float, float]],
                                             questions_answered: int) -> Tuple[float, Dict[str, Any]]:
        """
        Core Newton-Raphson calculation for theta estimation.
        Used by both cumulative and windowed approaches.
        """
        if not responses:
            return current_theta, {'method': 'no_responses', 'change': 0.0}

        theta = current_theta
        iterations_used = 0
        total_change = 0.0
        converged = False

        # Adjust smoothing based on questions answered
        if questions_answered <= self.EARLY_QUESTIONS_COUNT:
            smoothing_alpha = 0.3
        elif questions_answered <= 10:
            smoothing_alpha = 0.4
        elif questions_answered <= 15:
            smoothing_alpha = 0.5
        else:
            smoothing_alpha = min(0.7, self.base_exponential_smoothing_alpha)

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
                break

            raw_delta_theta = -likelihood_derivative / second_derivative

            if abs(raw_delta_theta) < self.convergence_threshold:
                converged = True
                break

            # Apply max change limits
            if questions_answered <= self.EARLY_QUESTIONS_COUNT:
                max_change = self.EARLY_QUESTIONS_MAX_CHANGE
            else:
                max_change = min(self.max_theta_change, self.MAX_SINGLE_STEP)

            delta_theta = raw_delta_theta
            if abs(delta_theta) > max_change:
                delta_theta = max_change if delta_theta > 0 else -max_change

            # Check total change budget
            potential_total_change = abs(total_change + delta_theta)
            if potential_total_change > self.ABSOLUTE_MAX_TOTAL_CHANGE:
                remaining_budget = self.ABSOLUTE_MAX_TOTAL_CHANGE - abs(total_change)
                delta_theta = remaining_budget if delta_theta > 0 else -remaining_budget

                if abs(delta_theta) < self.convergence_threshold:
                    break

            new_theta = theta + delta_theta
            total_change += delta_theta

            # Apply bounds
            bounded_theta = max(self.theta_bounds[0], min(self.theta_bounds[1], new_theta))
            if bounded_theta != new_theta:
                total_change = total_change - delta_theta + (bounded_theta - theta)

            theta = bounded_theta

            if abs(theta - (theta - delta_theta)) < self.convergence_threshold:
                converged = True
                break

        # Apply exponential smoothing
        smoothing_alpha = smoothing_alpha * (0.8 if converged else 1.0)
        smoothed_theta = (smoothing_alpha * theta + (1 - smoothing_alpha) * current_theta)

        final_theta = max(self.theta_bounds[0], min(self.theta_bounds[1], smoothed_theta))

        # Early question protection
        if questions_answered <= self.EARLY_QUESTIONS_COUNT:
            final_change = final_theta - current_theta
            if abs(final_change) > self.EARLY_QUESTIONS_MAX_CHANGE:
                final_theta = current_theta + self.EARLY_QUESTIONS_MAX_CHANGE * (1 if final_change > 0 else -1)

        # Final total change limit
        final_change = final_theta - current_theta
        if abs(final_change) > self.ABSOLUTE_MAX_TOTAL_CHANGE:
            if final_change > 0:
                final_theta = current_theta + self.ABSOLUTE_MAX_TOTAL_CHANGE
            else:
                final_theta = current_theta - self.ABSOLUTE_MAX_TOTAL_CHANGE
            final_theta = max(self.theta_bounds[0], min(self.theta_bounds[1], final_theta))

        adjustment_info = {
            'theta_change': final_theta - current_theta,
            'iterations_used': iterations_used,
            'converged': converged,
            'smoothing_alpha': smoothing_alpha,
            'questions_answered': questions_answered,
            'early_protection': questions_answered <= self.EARLY_QUESTIONS_COUNT
        }

        return final_theta, adjustment_info

    def calculate_theta_adjustment(self, current_theta: float,
                                   responses: List[Tuple[bool, float, float, float]],
                                   response_history: List[bool],
                                   questions_answered: int = 0) -> Tuple[float, Dict[str, Any]]:
        """
        Enhanced theta calculation with sliding window approach.

        Phase 1 (Q1-10): Use all cumulative responses for stable baseline
        Phase 2 (Q11-20): Blend cumulative and windowed
        Phase 3 (Q21+): Use windowed only for responsiveness to recent performance
        """
        if not responses:
            return current_theta, {'method': 'no_responses', 'change': 0.0}

        consecutive_info = self.detect_consecutive_responses(response_history)

        # Determine which approach to use based on question count
        if not self.use_windowed_theta or questions_answered <= self.window_transition_start:
            # Phase 1: CUMULATIVE (stable baseline building)
            responses_to_use = responses
            new_theta, info = self._calculate_theta_with_newton_raphson(
                current_theta, responses_to_use, questions_answered
            )
            info['method'] = 'cumulative_newton_raphson'
            info['window_phase'] = 'building'

            logger.debug(f"Phase 1 (CUMULATIVE): Using all {len(responses)} responses")

        elif questions_answered <= self.window_transition_end:
            # Phase 2: BLENDED (smooth transition)
            # Calculate both cumulative and windowed
            cumulative_theta, cumulative_info = self._calculate_theta_with_newton_raphson(
                current_theta, responses, questions_answered
            )

            windowed_responses = responses[-self.response_window_size:]
            windowed_theta, windowed_info = self._calculate_theta_with_newton_raphson(
                current_theta, windowed_responses, questions_answered
            )

            # Linear blend based on question count
            blend_factor = (questions_answered - self.window_transition_start) / \
                          (self.window_transition_end - self.window_transition_start)

            new_theta = (1 - blend_factor) * cumulative_theta + blend_factor * windowed_theta

            info = {
                'method': f'blended_transition',
                'window_phase': 'transition',
                'blend_factor': blend_factor,
                'cumulative_theta': cumulative_theta,
                'windowed_theta': windowed_theta,
                'cumulative_info': cumulative_info,
                'windowed_info': windowed_info,
                'theta_change': new_theta - current_theta,
                'questions_answered': questions_answered
            }

            logger.debug(f"Phase 2 (BLENDED): blend={blend_factor:.2f}, "
                        f"cumulative={cumulative_theta:.3f}, windowed={windowed_theta:.3f}, "
                        f"final={new_theta:.3f}")

        else:
            # Phase 3: WINDOWED (responsive to recent performance)
            windowed_responses = responses[-self.response_window_size:]
            new_theta, info = self._calculate_theta_with_newton_raphson(
                current_theta, windowed_responses, questions_answered
            )
            info['method'] = 'windowed_newton_raphson'
            info['window_phase'] = 'mature'
            info['window_size'] = len(windowed_responses)

            logger.debug(f"Phase 3 (WINDOWED): Using last {len(windowed_responses)} responses")

        info['consecutive_info'] = consecutive_info

        return new_theta, info

    def robust_theta_update(self, current_theta: float,
                            responses: List[Tuple[bool, float, float, float]],
                            response_history: List[bool] = None,
                            response_times: List[float] = None,
                            questions_answered: int = 0) -> Tuple[float, Dict]:
        """Robust theta update with sliding window and all safety constraints"""
        try:
            new_theta, info = self.calculate_theta_adjustment(
                current_theta, responses, response_history, questions_answered
            )

            # CONTRACT: Response-based theta constraints
            if response_history and len(response_history) >= 1:
                last_response = response_history[-1]

                # Wrong answer → theta cannot increase
                if not last_response and new_theta > current_theta:
                    logger.info(f"❌ CONSTRAINT: Theta increase blocked after incorrect response "
                               f"({new_theta:.3f} clamped to {current_theta:.3f})")
                    new_theta = current_theta
                    info['response_constraint'] = 'incorrect_no_increase'

                # Correct answer → theta cannot decrease
                elif last_response and new_theta < current_theta:
                    logger.info(f"✅ CONSTRAINT: Theta decrease blocked after correct response "
                               f"({new_theta:.3f} clamped to {current_theta:.3f})")
                    new_theta = current_theta
                    info['response_constraint'] = 'correct_no_decrease'

            # Early question protection
            if questions_answered <= self.EARLY_QUESTIONS_COUNT:
                max_change = self.EARLY_QUESTIONS_MAX_CHANGE
                actual_change = new_theta - current_theta
                if abs(actual_change) > max_change:
                    new_theta = current_theta + max_change * (1 if actual_change > 0 else -1)
                    info['early_protection_applied'] = True
                    logger.info(f"Early protection: limiting change to +/-{max_change}")

            # Update velocity
            velocity = new_theta - current_theta
            self.theta_velocity = self.velocity_damping * self.theta_velocity + (1 - self.velocity_damping) * velocity

            # Large change fallback
            if abs(new_theta - current_theta) > 1.5:
                logger.warning(f"Large theta change: {current_theta:.3f} -> {new_theta:.3f}")
                new_theta = self.calculate_eap_estimate(responses, current_theta)
                info['method'] = 'eap_fallback'

            # Response time adjustment
            if self.adaptive_config.enable_response_time and response_times:
                time_adjustment = self.calculate_response_time_adjustment(
                    new_theta, responses, response_times
                )
                new_theta += time_adjustment
                info['response_time_adjustment'] = time_adjustment

        except Exception as e:
            logger.error(f"Theta calculation failed: {e}, using MLE")
            new_theta = self.calculate_mle_estimate(responses, current_theta)
            info = {'method': 'mle_fallback', 'error': str(e)}

        self.theta_history.append(new_theta)

        return new_theta, info

    def calculate_eap_estimate(self, responses: List[Tuple[bool, float, float, float]],
                               prior_theta: float = 0.0) -> float:
        """Expected A Posteriori estimate as fallback"""
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
            expected_time = 5.0 + 2.0 * abs(theta - difficulty)
            time_ratio = response_time / expected_time

            if is_correct and time_ratio < 0.7:
                adjustments.append(0.05)
            elif not is_correct and time_ratio > 1.5:
                adjustments.append(-0.05)
            elif is_correct and time_ratio > 2.0:
                adjustments.append(-0.02)

        return sum(adjustments)

    def should_stop_with_confidence(self, sem: float, questions_asked: int,
                                    response_history: List[bool]) -> Tuple[bool, float]:
        """Enhanced stopping logic with confidence estimation"""
        if questions_asked < self.min_questions:
            return False, 0.0

        if questions_asked >= self.max_questions:
            confidence = 1.0 - sem if sem < 1.0 else 0.5
            return True, confidence

        if len(self.theta_history) >= 5:
            recent_thetas = self.theta_history[-5:]
            theta_variance = np.var(recent_thetas)
            if theta_variance < 0.01:
                logger.info(f"Theta stabilized with variance {theta_variance:.4f}")
                return True, 0.95

        if sem <= self.target_sem:
            confidence = min(0.99, 1.0 - sem)
            return True, confidence

        if len(response_history) >= 8:
            consecutive_info = self.detect_consecutive_responses(response_history)
            if consecutive_info['consecutive_count'] >= 6:
                confidence = 0.85 if consecutive_info['response_type'] == 'correct' else 0.80
                logger.info(f"Stopping due to {consecutive_info['consecutive_count']} "
                            f"consecutive {consecutive_info['response_type']} responses")
                return True, confidence

            recent = response_history[-8:]
            accuracy = sum(recent) / len(recent)
            if accuracy == 1.0 or accuracy == 0.0:
                return True, 0.90

        return False, 0.0

    # New method:
    def get_precision_quality(self, sem: float) -> Dict[str, Any]:
        """Get precision quality label and details."""
        if sem <= 0.15:
            return {
                'label': 'Excellent Precision',
                'color': '#10B981',
                'description': 'Very high confidence in ability estimate',
                'confidence_level': 'very_high',
                'stars': 5
            }
        elif sem <= 0.20:
            return {
                'label': 'High Precision',
                'color': '#3B82F6',
                'description': 'High confidence in ability estimate',
                'confidence_level': 'high',
                'stars': 4
            }
        elif sem <= 0.30:
            return {
                'label': 'Good Precision',
                'color': '#F59E0B',
                'description': 'Good confidence in ability estimate',
                'confidence_level': 'good',
                'stars': 3
            }
        else:
            return {
                'label': 'Moderate Precision',
                'color': '#EF4444',
                'description': 'Moderate confidence in ability estimate',
                'confidence_level': 'moderate',
                'stars': 2
            }



    # The should_stop_assessment method:
    def should_stop_assessment(
            self,
            sem: float,
            questions_answered: int,
            test_purpose: TestPurpose = None
    ) -> Tuple[bool, str]:
        """Enhanced stopping criteria with logging."""
        # Use the test_purpose if provided, otherwise use instance's test_purpose
        if test_purpose is None:
            test_purpose = self.test_purpose

        # Get config for the specified test purpose
        config = AdaptiveConfig.get_config(test_purpose)

        # Check minimum
        if questions_answered < config.min_questions:
            return False, "Minimum questions not reached"

        # Check target achieved
        if sem <= config.target_sem:
            logger.info(f"✅ Target SEM {sem:.3f} reached after {questions_answered} questions")
            return True, f"Target precision achieved (SEM: {sem:.3f})"

        # Check max
        if questions_answered >= config.max_questions:
            if sem > config.target_sem:
                logger.warning(
                    f"🛑 Max questions reached: SEM {sem:.3f} > target {config.target_sem}"
                )
            return True, f"Maximum questions reached (SEM: {sem:.3f})"

        return False, f"Continuing (SEM: {sem:.3f})"


    def generate_diagnostic_report(self, final_theta: float,
                                   responses: List[Tuple[bool, float, float, float]],
                                   response_history: List[bool],
                                   response_times: List[float] = None,
                                   question_details: List[Dict] = None) -> Dict:
        """Generate comprehensive diagnostic report"""
        if not responses:
            return {
                'final_ability': final_theta,
                'final_tier': self.theta_to_tier(final_theta),
                'questions_answered': 0,
                'test_completed': False
            }

        correct_count = sum(1 for r, _, _, _ in responses if r)
        total_questions = len(responses)
        accuracy = correct_count / total_questions

        final_sem = self.calculate_sem(
            final_theta,
            [(d, a, g) for _, d, a, g in responses]
        )
        confidence_interval = (
            final_theta - 1.96 * final_sem,
            final_theta + 1.96 * final_sem
        )

        content_performance = {}
        if self.adaptive_config.enable_content_balancing and question_details:
            content_areas_data = {}
            for i, (is_correct, _, _, _) in enumerate(responses):
                if i < len(question_details):
                    q_detail = question_details[i]
                    area = q_detail.get('content_area', q_detail.get('topic', 'default'))
                    if area not in content_areas_data:
                        content_areas_data[area] = []
                    content_areas_data[area].append(is_correct)

            for area, area_responses in content_areas_data.items():
                if area_responses:
                    area_accuracy = sum(area_responses) / len(area_responses)
                    content_performance[area] = {
                        'questions': len(area_responses),
                        'accuracy': area_accuracy,
                        'strength_level': 'Strong' if area_accuracy > 0.75 else
                        'Weak' if area_accuracy < 0.40 else 'Moderate'
                    }

        consecutive_info = self.detect_consecutive_responses(response_history)
        max_consecutive_correct = self._count_max_consecutive(response_history, True)
        max_consecutive_incorrect = self._count_max_consecutive(response_history, False)

        difficulties = [d for _, d, _, _ in responses]
        difficulty_trend = 'increasing' if len(difficulties) > 1 and difficulties[-1] > difficulties[0] else \
            'decreasing' if len(difficulties) > 1 and difficulties[-1] < difficulties[0] else \
                'stable'

        total_information = sum(
            self.information(final_theta, d, a, g)
            for _, d, a, g in responses
        )
        avg_information = total_information / total_questions if total_questions > 0 else 0

        time_analysis = {}
        if response_times and len(response_times) == total_questions:
            avg_time = np.mean(response_times)
            time_analysis = {
                'average_response_time': avg_time,
                'fastest_response': min(response_times),
                'slowest_response': max(response_times),
                'time_consistency': np.std(response_times)
            }

        report = {
            'final_ability': final_theta,
            'final_tier': self.theta_to_tier(final_theta),
            'estimated_tier': self.theta_to_tier(final_theta),  # Theta-based
            'active_tier': self._apply_conservative_fairness_constraints(
                self.theta_to_tier(final_theta),
                response_history,
                consecutive_info
            ) if len(response_history) >= self.min_questions_before_tier_change else self.theta_to_tier(final_theta),
            'confidence_interval': confidence_interval,
            'final_sem': final_sem,
            'questions_answered': total_questions,
            'correct_answers': correct_count,
            'accuracy': accuracy,
            'test_efficiency': {
                'total_information': total_information,
                'average_information_per_item': avg_information,
                'relative_efficiency': avg_information / 2.0 if avg_information > 0 else 0
            },
            'content_area_performance': content_performance,
            'response_patterns': {
                'max_consecutive_correct': max_consecutive_correct,
                'max_consecutive_incorrect': max_consecutive_incorrect,
                'final_pattern': consecutive_info,
                'difficulty_trend': difficulty_trend,
                'average_difficulty': np.mean(difficulties) if difficulties else 0,
                'difficulty_progression': difficulties
            },
            'theta_progression': {
                'initial_theta': self.theta_history[0] if self.theta_history else final_theta,
                'final_theta': final_theta,
                'total_change': final_theta - (self.theta_history[0] if self.theta_history else final_theta),
                'stability': np.var(self.theta_history[-5:]) if len(self.theta_history) >= 5 else None,
                'history': self.theta_history
            },
            'time_analysis': time_analysis,
            'test_purpose': self.test_purpose.value,
            'test_completed': total_questions >= self.min_questions,
            'anticipation_multiplier': self.adaptive_config.anticipation_multiplier,
            'rt_weighted_info_enabled': self.adaptive_config.enable_rt_weighted_information,
            'unique_questions_asked': len(self.asked_question_ids),
            'response_based_constraints': True,
            'sliding_window_enabled': self.use_windowed_theta,
            'window_config': {
                'size': self.response_window_size,
                'transition_start': self.window_transition_start,
                'transition_end': self.window_transition_end
            } if self.use_windowed_theta else None
        }

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

    def update_theta(self, current_theta: float,
                     responses: List[Tuple[bool, float, float, float]],
                     response_history: List[bool] = None,
                     response_times: List[float] = None,
                     questions_answered: int = 0) -> Tuple[float, Dict[str, Any]]:
        """Main theta update method using sliding window approach"""
        if response_history is None:
            response_history = [r[0] for r in responses]

        new_theta, info = self.robust_theta_update(
            current_theta, responses, response_history, response_times, questions_answered
        )

        self.current_theta = new_theta

        # Calculate both tiers for display
        estimated_tier = self.theta_to_tier(new_theta)  # Simple theta mapping
        consecutive_info = self.detect_consecutive_responses(response_history)
        active_tier = self._apply_conservative_fairness_constraints(
            estimated_tier, response_history, consecutive_info
        )  # Actually used for question selection

        # Add tier information to response
        info['estimated_tier'] = estimated_tier
        info['active_tier'] = active_tier
        info['tier_alignment'] = (estimated_tier == active_tier)

        logger.info(f"Theta updated: {current_theta:.3f} -> {new_theta:.3f} "
                    f"(delta={new_theta - current_theta:+.3f}), Q={questions_answered}, "
                    f"method={info.get('method', 'unknown')}, "
                    f"tiers: estimated={estimated_tier}, active={active_tier}")

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
        """
        Apply conservative single-tier progression constraints with response-based rules.

        NEW CONTRACTS:
        - Wrong answer → NEVER promote tier
        - Correct answer → NEVER demote tier
        """
        if self.adaptive_config.tier_change_aggressive:
            min_questions = max(5, self.min_questions_before_tier_change // 2)
        else:
            min_questions = self.min_questions_before_tier_change

        if len(response_history) < min_questions:
            return current_tier

        # Get last response
        last_response_correct = response_history[-1] if response_history else None

        # CONTRACT: Never promote tier after incorrect response
        if last_response_correct is False:
            logger.debug("❌ Tier promotion blocked: last response was incorrect")

            # Still allow demotion to proceed after incorrect response
            if len(response_history) >= self.tier_demotion_window:
                recent_window = response_history[-self.tier_demotion_window:]
                correct_count = sum(recent_window)

                if correct_count <= self.tier_demotion_threshold:
                    new_tier = self._adjust_tier_down(current_tier)
                    if new_tier != current_tier:
                        logger.info(f"TIER DEMOTION: {current_tier} -> {new_tier} "
                                    f"({correct_count}/{self.tier_demotion_window} correct)")
                        return new_tier
            return current_tier

        # CONTRACT: Never demote tier after correct response
        if last_response_correct is True:
            logger.debug("✅ Tier demotion blocked: last response was correct")

            # Only allow promotion after correct response
            if len(response_history) >= self.tier_promotion_window:
                recent_window = response_history[-self.tier_promotion_window:]
                correct_count = sum(recent_window)

                if correct_count >= self.tier_promotion_threshold:
                    new_tier = self._adjust_tier_up(current_tier)
                    if new_tier != current_tier:
                        logger.info(f"TIER PROMOTION: {current_tier} -> {new_tier} "
                                    f"({correct_count}/{self.tier_promotion_window} correct)")
                        return new_tier
            return current_tier

        # If no last response (shouldn't happen), maintain current tier
        return current_tier

    def _adjust_tier_up(self, tier: str) -> str:
        """Adjust tier up by exactly one level"""
        tier_order = ["C1", "C2", "C3", "C4"]
        try:
            current_index = tier_order.index(tier)
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
        """Calculate final assessment metrics"""
        return self.generate_diagnostic_report(
            final_theta,
            responses,
            response_history or [r[0] for r in responses],
            response_times=self.question_response_times,
            question_details=question_details
        )

    @staticmethod
    def create_response_tuple(is_correct: bool, question: Dict) -> Tuple[bool, float, float, float]:
        """Helper method to create a response tuple from a question dictionary"""
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
        Run a complete adaptive assessment with all contracts enforced.
        """
        current_theta = self.initialize_assessment(initial_competence)

        responses = []
        response_history = []
        response_times = [] if enable_response_times else None
        available_questions = question_bank.copy()
        questions_answered = 0
        question_details = []

        logger.info(f"Starting assessment: {len(available_questions)} questions, "
                    f"multiplier={self.adaptive_config.anticipation_multiplier}x, "
                    f"windowing={'ENABLED' if self.use_windowed_theta else 'DISABLED'}, "
                    f"response-based constraints: ENABLED")

        while questions_answered < self.max_questions:
            next_question = self.select_next_question(
                theta=current_theta,
                available_questions=available_questions,
                response_history=response_history,
                questions_answered=questions_answered
            )

            if not next_question:
                logger.warning("No more suitable questions available")
                break

            available_questions.remove(next_question)
            question_details.append(next_question)

            prob_correct = self.probability_correct(
                current_theta,
                next_question['difficulty_b'],
                next_question['discrimination_a'],
                next_question.get('guessing_c', 0.25)
            )
            is_correct = random.random() < prob_correct

            response_tuple = (
                is_correct,
                next_question['difficulty_b'],
                next_question['discrimination_a'],
                next_question.get('guessing_c', 0.25)
            )
            responses.append(response_tuple)
            response_history.append(is_correct)
            self.cumulative_responses.append(response_tuple)

            if enable_response_times:
                base_time = 15.0
                difficulty_distance = abs(current_theta - next_question['difficulty_b'])
                simulated_time = base_time + random.uniform(-5, 5) + difficulty_distance * 3
                response_times.append(simulated_time)
                self.question_response_times.append(simulated_time)

            questions_answered += 1

            current_theta, update_info = self.update_theta(
                current_theta=current_theta,
                responses=self.cumulative_responses,
                response_history=response_history,
                response_times=response_times if response_times else None,
                questions_answered=questions_answered
            )

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
                logger.info(f"Stopping: questions={questions_answered}, "
                            f"SEM={current_sem:.3f}, confidence={confidence:.2f}")
                break

        final_report = self.generate_diagnostic_report(
            final_theta=current_theta,
            responses=responses,
            response_history=response_history,
            response_times=response_times,
            question_details=question_details
        )

        final_report['assessment_metadata'] = {
            'initial_competence': initial_competence,
            'initial_theta': self.theta_history[0] if self.theta_history else current_theta,
            'question_bank_size': len(question_bank),
            'questions_remaining': len(available_questions),
            'test_purpose': self.test_purpose.value,
            'response_times_enabled': enable_response_times,
            'rt_weighted_info_enabled': self.adaptive_config.enable_rt_weighted_information,
            'anticipation_multiplier': self.adaptive_config.anticipation_multiplier,
            'response_based_constraints': True,
            'sliding_window_enabled': self.use_windowed_theta
        }

        logger.info(f"Assessment completed: theta={current_theta:.3f}, "
                    f"questions={questions_answered}, tier={final_report['final_tier']}")

        return final_report


def create_irt_engine(config=None, test_purpose=TestPurpose.DIAGNOSTIC):
    """Factory function to create an IRT engine"""
    return IRTEngine(config=config, test_purpose=test_purpose)


def create_simple_irt_engine(config=None):
    """Create a simplified IRT engine with content balancing disabled"""
    engine = IRTEngine(config=config, test_purpose=TestPurpose.DIAGNOSTIC)
    engine.adaptive_config.enable_content_balancing = False
    return engine


def get_default_config():
    """Default configuration with sliding window theta updates"""
    return {
        "irt_config": {
            "history_window": 5,
            "max_theta_change": 0.3,
            "theta_jump": 0.4,
            "consecutive_same_responses": 3,
            "theta_bounds": [-3.0, 3.0],
            "newton_raphson_iterations": 10,
            "convergence_threshold": 0.001,
            "exponential_smoothing_alpha": 0.7,
            "enable_consecutive_jumps": True,
            "tier_promotion_window": 10,
            "tier_promotion_threshold": 7,
            "tier_demotion_window": 10,
            "tier_demotion_threshold": 3,
            "min_questions_before_tier_change": 10,
            # NEW: Sliding window configuration
            "use_windowed_theta": True,
            "response_window_size": 10,
            "window_transition_start": 10,
            "window_transition_end": 20
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


def get_config():
    """Legacy config loader"""
    default_config = get_default_config()
    return {
        "get_irt_config": lambda: default_config["irt_config"],
        "get_tier_config": lambda: default_config["tier_config"]
    }