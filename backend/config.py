import os
from typing import Dict, Tuple


class Config:
    """Configuration class for Adaptive Assessment System"""

    # Database Configuration
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./adaptive_assessment.db")

    # IRT Engine Configuration
    IRT_CONFIG = {
        # Note: Cleanup : Remove target_sem - it's in AdaptiveConfig now
        "target_sem": float(os.getenv("TARGET_SEM", "0.13")),
        "max_questions": int(os.getenv("MAX_QUESTIONS", "40")),
        "min_questions": int(os.getenv("MIN_QUESTIONS", "8")),
        "history_window": int(os.getenv("HISTORY_WINDOW", "8")),
        "max_theta_change": float(os.getenv("MAX_THETA_CHANGE", "0.1")),
        "theta_jump": float(os.getenv("THETA_JUMP", "0.15")),  # ← NEW: For consecutive responses
        "consecutive_same_responses": int(os.getenv("CONSECUTIVE_SAME_RESPONSES", "6")),  # ← NEW
        "enable_consecutive_jumps": os.getenv("ENABLE_CONSECUTIVE_JUMPS", "true").lower() == "true",  # ← NEW
        "theta_bounds": (-2.0, 2.0),
        "newton_raphson_iterations": int(os.getenv("NR_ITERATIONS", "10")),
        "convergence_threshold": float(os.getenv("CONVERGENCE_THRESHOLD", "0.01")),
        "exponential_smoothing_alpha": float(os.getenv("EXP_SMOOTH_ALPHA", "0.7")),
        # Conservative tier progression parameters
        "tier_promotion_window": int(os.getenv("TIER_PROMOTION_WINDOW", "8")),
        "tier_promotion_threshold": int(os.getenv("TIER_PROMOTION_THRESHOLD", "6")),  # 6 out of 8
        "tier_demotion_window": int(os.getenv("TIER_DEMOTION_WINDOW", "8")),
        "tier_demotion_threshold": int(os.getenv("TIER_DEMOTION_THRESHOLD", "2")),  # 2 out of 8
        "min_questions_before_tier_change": int(os.getenv("MIN_QUESTIONS_TIER_CHANGE", "8"))
    }

    # Tier Configuration
    TIER_THETA_RANGES: Dict[str, Tuple[float, float]] = {
        "C1": (-2.0, -1.0),
        "C2": (-1.0, 0.0),
        "C3": (0.0, 1.0),
        "C4": (1.0, 2.0)
    }

    # TIER_DISCRIMINATION_RANGES: Dict[str, Tuple[float, float]] = {
    #     "C1": (0.8, 1.0),
    #     "C2": (1.0, 1.4),
    #     "C3": (1.0, 1.4),
    #     "C4": (1.4, 1.6)
    # }

    # # MORE FLEXIBLE
    # TIER_DISCRIMINATION_RANGES = {
    #     "C1": (0.7, 1.2),  # Allow lower for easier items
    #     "C2": (0.9, 1.6),  # Wider range for flexibility
    #     "C3": (1.0, 1.8),  # Higher ceiling for better items
    #     "C4": (1.3, 2.0)  # Allow higher discrimination
    # }

    # Maximum Safe (Aggressive) - HIGH PERFORMANCE
    TIER_DISCRIMINATION_RANGES = {
        "C1": (0.6, 1.3),
        "C2": (0.8, 1.8),
        "C3": (1.0, 2.2),
        "C4": (1.2, 2.5)  # Near theoretical maximum
    }


    TIER_DIFFICULTY_RANGES: Dict[str, Tuple[float, float]] = {
        "C1": (-1.5, -0.5),
        "C2": (-0.5, 0.5),
        "C3": (0.5, 1.0),
        "C4": (1.0, 2.0)
    }

    # Initial theta values for competence levels
    INITIAL_THETA_MAP: Dict[str, float] = {
        "C1": -1.5,
        "C2": -0.5,
        "C3": 0.5,
        "C4": 1.5
    }

    # API Configuration
    API_CONFIG = {
        "host": os.getenv("API_HOST", "0.0.0.0"),
        "port": int(os.getenv("API_PORT", "8000")),
        "cors_origins": os.getenv("CORS_ORIGINS", "http://localhost:3000").split(","),
        "title": "Adaptive Assessment API",
        "version": "1.0.0"
    }

    # Logging Configuration
    LOGGING_CONFIG = {
        "level": os.getenv("LOG_LEVEL", "INFO"),
        "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        "log_file": os.getenv("LOG_FILE", "adaptive_assessment.log"),
    }

    @classmethod
    def get_irt_config(cls):
        """Get IRT configuration"""
        return cls.IRT_CONFIG

    @classmethod
    def get_tier_config(cls):
        """Get tier configuration"""
        return {
            "theta_ranges": cls.TIER_THETA_RANGES,
            "discrimination_ranges": cls.TIER_DISCRIMINATION_RANGES,
            "difficulty_ranges": cls.TIER_DIFFICULTY_RANGES,
            "initial_theta_map": cls.INITIAL_THETA_MAP
        }

    @classmethod
    def validate_config(cls):
        """Validate configuration values"""
        errors = []

        # Validate IRT config
        if cls.IRT_CONFIG["target_sem"] <= 0:
            errors.append("TARGET_SEM must be positive")

        if cls.IRT_CONFIG["min_questions"] >= cls.IRT_CONFIG["max_questions"]:
            errors.append("MIN_QUESTIONS must be less than MAX_QUESTIONS")

        if cls.IRT_CONFIG["theta_jump"] <= cls.IRT_CONFIG["max_theta_change"]:
            errors.append("THETA_JUMP should be larger than MAX_THETA_CHANGE")

        if errors:
            raise ValueError(f"Configuration errors: {', '.join(errors)}")

        return True


def get_config():
    """Get configuration based on environment"""
    return Config()