# backend/services.py
"""
FULLY BACKWARD COMPATIBLE SERVICES
All changes are ADDITIVE with safety mechanisms
Admin module will continue to work unchanged
"""





import matplotlib
matplotlib.use('Agg')  # Use non-GUI backend - MUST be before pyplot import
import matplotlib.pyplot as plt
import numpy as np

from sqlalchemy.orm import Session
from sqlalchemy import and_, not_, text
from typing import List, Optional, Dict, Tuple
import pandas as pd
from datetime import datetime
import logging
import sys
import os
import time
import json
from collections import defaultdict
import sqlite3
from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus.flowables import HRFlowable



sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'scripts'))
from db_manager import item_bank_db

import models_registry
import models_itembank
from irt_engine import IRTEngine
import schemas

logger = logging.getLogger(__name__)


# ========== NEW CLASS - Doesn't affect existing code ==========

class TopicPerformanceCalculator:
    """NEW: Calculate per-topic theta and performance metrics"""

    @staticmethod
    def calculate_topic_theta(responses: List, topic: str, irt_engine: IRTEngine) -> Optional[Dict]:
        """Calculate theta for specific topic based on responses"""
        topic_responses = [r for r in responses if r.get('topic') == topic]

        if not topic_responses:
            return None

        response_tuples = [
            (r['is_correct'], r['difficulty'], r['discrimination'], r['guessing'])
            for r in topic_responses
        ]

        correct_count = sum(1 for r in topic_responses if r['is_correct'])
        initial_theta = -1.0 + (correct_count / len(topic_responses)) * 2.0

        try:
            topic_theta, _ = irt_engine.update_theta(
                current_theta=initial_theta,
                responses=response_tuples,
                response_history=[r['is_correct'] for r in topic_responses],
                questions_answered=len(topic_responses)
            )

            questions_info = [(r['difficulty'], r['discrimination'], r['guessing'])
                              for r in topic_responses]
            topic_sem = irt_engine.calculate_sem(topic_theta, questions_info)

            accuracy = correct_count / len(topic_responses)

            return {
                'topic': topic,
                'theta': round(topic_theta, 2),
                'sem': round(topic_sem, 2),
                'tier': irt_engine.theta_to_tier(topic_theta),
                'questions_answered': len(topic_responses),
                'correct_count': correct_count,
                'accuracy': round(accuracy, 2),
                'strength_level': TopicPerformanceCalculator.get_strength_level(accuracy)
            }
        except Exception as e:
            logger.debug(f"Could not calculate topic theta for {topic}: {e}")
            return None

    @staticmethod
    def get_strength_level(accuracy: float) -> str:
        """Determine strength level based on accuracy"""
        if accuracy >= 0.80:
            return 'Strong'
        elif accuracy >= 0.60:
            return 'Proficient'
        elif accuracy >= 0.40:
            return 'Developing'
        else:
            return 'Needs Practice'

    @staticmethod
    def generate_learning_roadmap(topic_performance: Dict, overall_theta: float) -> Dict:
        """Generate personalized learning roadmap"""
        if not topic_performance:
            return None

        topics = list(topic_performance.values())

        strong_topics = [t for t in topics if t.get('strength_level') == 'Strong']
        proficient_topics = [t for t in topics if t.get('strength_level') == 'Proficient']
        developing_topics = [t for t in topics if t.get('strength_level') == 'Developing']
        weak_topics = [t for t in topics if t.get('strength_level') == 'Needs Practice']

        recommendations = []
        priority_topics = []

        if weak_topics:
            priority_topics = [t['topic'] for t in weak_topics[:3]]
            recommendations.append({
                'type': 'immediate_focus',
                'title': 'Priority Areas',
                'topics': priority_topics,
                'description': 'Start with these topics to build a strong foundation.',
                'action': 'Practice 5-10 questions daily'
            })

        if developing_topics:
            recommendations.append({
                'type': 'practice_more',
                'title': 'Continue Practicing',
                'topics': [t['topic'] for t in developing_topics[:3]],
                'description': 'You\'re making progress! Keep practicing to master these areas.',
                'action': 'Solve 3-5 problems daily'
            })

        if strong_topics:
            recommendations.append({
                'type': 'maintain',
                'title': 'Maintain Strengths',
                'topics': [t['topic'] for t in strong_topics],
                'description': 'Great job! Review periodically to stay sharp.',
                'action': 'Weekly revision recommended'
            })

        if overall_theta >= 1.0:
            overall_message = "Excellent work! You've demonstrated strong mastery across topics."
        elif overall_theta >= 0.0:
            overall_message = "Good progress! Focus on weak areas to reach the next level."
        elif overall_theta >= -1.0:
            overall_message = "You're building foundational skills. Consistent practice will help you improve."
        else:
            overall_message = "Start with basics and build gradually. Every step forward counts!"

        return {
            'overall_message': overall_message,
            'recommendations': recommendations,
            'priority_topics': priority_topics,
            'strengths': [t['topic'] for t in strong_topics],
            'weaknesses': [t['topic'] for t in weak_topics],
            'next_milestone': TopicPerformanceCalculator.get_next_milestone(overall_theta)
        }

    @staticmethod
    def get_next_milestone(current_theta: float) -> Dict:
        """Get next performance milestone"""
        if current_theta < -1.0:
            return {
                'target_tier': 'Intermediate (C2)',
                'target_theta': -0.5,
                'estimated_questions': 20,
                'focus': 'Master foundational concepts'
            }
        elif current_theta < 0.0:
            return {
                'target_tier': 'Advanced (C3)',
                'target_theta': 0.5,
                'estimated_questions': 15,
                'focus': 'Practice complex problem-solving'
            }
        elif current_theta < 1.0:
            return {
                'target_tier': 'Expert (C4)',
                'target_theta': 1.5,
                'estimated_questions': 20,
                'focus': 'Challenge yourself with advanced topics'
            }
        else:
            return {
                'target_tier': 'Master',
                'target_theta': 2.0,
                'estimated_questions': 25,
                'focus': 'Explore competition-level problems'
            }


# ========== NEW CLASS - PDF Export Service ==========


class PDFExportService:
    """Clean PDF Export Service - Essential Sections Only"""

    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
        self._register_fonts()

    def _register_fonts(self):
        """Register Unicode-compatible fonts from bundled font files"""
        import os

        try:
            # Get the directory where this services.py file is located
            current_dir = os.path.dirname(os.path.abspath(__file__))

            # Path to bundled fonts
            fonts_dir = os.path.join(current_dir, 'fonts', 'dejavu-fonts-ttf-2.37', 'ttf')

            # Font file paths
            regular_font = os.path.join(fonts_dir, 'DejaVuSans.ttf')
            bold_font = os.path.join(fonts_dir, 'DejaVuSans-Bold.ttf')

            # Check if fonts exist
            if os.path.exists(regular_font) and os.path.exists(bold_font):
                pdfmetrics.registerFont(TTFont('DejaVuSans', regular_font))
                pdfmetrics.registerFont(TTFont('DejaVuSans-Bold', bold_font))
                self.unicode_font = 'DejaVuSans'
                self.unicode_font_bold = 'DejaVuSans-Bold'
                logger.info(f"Successfully registered DejaVu fonts from: {fonts_dir}")
            else:
                raise FileNotFoundError(f"Font files not found at: {fonts_dir}")

        except Exception as e:
            # Fallback: Use sanitized text with Helvetica
            logger.warning(f"Could not load DejaVu fonts: {e}. Using Helvetica with text sanitization.")
            self.unicode_font = 'Helvetica'
            self.unicode_font_bold = 'Helvetica-Bold'

    def _sanitize_text(self, text: str) -> str:
        """
        Convert mathematical Unicode characters to readable ASCII alternatives
        if proper Unicode fonts are not available
        """
        if not text:
            return text

        # Map common mathematical Unicode to ASCII alternatives
        replacements = {
            # Subscripts
            '₀': '_0', '₁': '_1', '₂': '_2', '₃': '_3', '₄': '_4',
            '₅': '_5', '₆': '_6', '₇': '_7', '₈': '_8', '₉': '_9',
            # Superscripts
            '⁰': '^0', '¹': '^1', '²': '^2', '³': '^3', '⁴': '^4',
            '⁵': '^5', '⁶': '^6', '⁷': '^7', '⁸': '^8', '⁹': '^9',
            # Greek letters (common in math)
            'α': 'alpha', 'β': 'beta', 'γ': 'gamma', 'δ': 'delta',
            'θ': 'theta', 'λ': 'lambda', 'μ': 'mu', 'π': 'pi',
            'σ': 'sigma', 'τ': 'tau', 'φ': 'phi', 'ω': 'omega',
            # Mathematical symbols
            '√': 'sqrt', '∞': 'infinity', '≈': '~=', '≠': '!=',
            '≤': '<=', '≥': '>=', '±': '+/-', '×': 'x', '÷': '/',
        }

        result = text
        for unicode_char, ascii_replacement in replacements.items():
            result = result.replace(unicode_char, ascii_replacement)

        return result

    def _setup_custom_styles(self):
        """Setup custom styles for PDF"""
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Title'],
            fontSize=24,
            textColor=colors.HexColor('#2E86C1'),
            spaceAfter=30,
            alignment=TA_CENTER
        ))

        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#34495E'),
            spaceBefore=20,
            spaceAfter=10
        ))

        self.styles.add(ParagraphStyle(
            name='Subsection',
            parent=self.styles['Heading3'],
            fontSize=12,
            textColor=colors.HexColor('#5D6D7E'),
            spaceBefore=12,
            spaceAfter=6
        ))

    def _generate_theta_progression_chart(self, responses: list) -> BytesIO:
        """Generate theta progression line chart"""
        try:
            if not responses or len(responses) == 0:
                logger.warning("No responses provided for theta progression chart")
                return None

            fig, ax = plt.subplots(figsize=(8, 4))

            questions = [i + 1 for i in range(len(responses))]
            theta_values = [r.get('theta_after', 0) for r in responses]

            # Plot line
            ax.plot(questions, theta_values, 'b-', linewidth=2, label='Theta (θ)')

            # Mark correct/incorrect with different colors
            for i, resp in enumerate(responses):
                color = 'green' if resp.get('is_correct', False) else 'red'
                ax.scatter(i + 1, resp.get('theta_after', 0), c=color, s=60, zorder=5)

            ax.set_xlabel('Question Number', fontsize=11)
            ax.set_ylabel('Theta (θ)', fontsize=11)
            ax.set_title('Proficiency estimate over time', fontsize=12, fontweight='bold')
            ax.grid(True, alpha=0.3)

            # Create custom legend
            from matplotlib.lines import Line2D
            legend_elements = [
                Line2D([0], [0], marker='o', color='w', markerfacecolor='green',
                       markersize=8, label='Correct'),
                Line2D([0], [0], marker='o', color='w', markerfacecolor='red',
                       markersize=8, label='Incorrect')
            ]
            ax.legend(handles=legend_elements, loc='best')

            plt.tight_layout()
            buffer = BytesIO()
            plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
            buffer.seek(0)
            plt.close(fig)

            return buffer

        except Exception as e:
            logger.error(f"Error generating theta progression chart: {e}", exc_info=True)
            plt.close('all')
            return None

    def _generate_topic_radar(self, topic_performance: dict) -> BytesIO:
        """Generate radar chart for topic performance"""
        try:
            topics = list(topic_performance.keys())
            if not topics or len(topics) == 0:
                return None

            accuracies = [topic_performance[t]['accuracy'] * 100 for t in topics]

            # Number of topics
            num_vars = len(topics)

            # Compute angle for each axis
            angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()
            accuracies += accuracies[:1]  # Complete the circle
            angles += angles[:1]

            fig, ax = plt.subplots(figsize=(7, 7), subplot_kw=dict(projection='polar'))

            # Plot accuracy
            ax.plot(angles, accuracies, 'o-', linewidth=2, color='#10B981', label='Accuracy %')
            ax.fill(angles, accuracies, alpha=0.25, color='#10B981')

            # Normalize theta values for plotting (theta ranges from -3 to 3, map to 0-100)
            theta_normalized = [((topic_performance[t]['theta'] + 3) / 6) * 100 for t in topics]
            theta_normalized += theta_normalized[:1]

            ax.plot(angles, theta_normalized, 'o-', linewidth=2, color='#3B82F6', label='Proficiency (normalized)')
            ax.fill(angles, theta_normalized, alpha=0.15, color='#3B82F6')

            ax.set_xticks(angles[:-1])
            ax.set_xticklabels([t.replace('Complex Numbers - ', '').replace('complex numbers - ', '')
                                for t in topics], size=9)
            ax.set_ylim(0, 100)
            ax.set_yticks([25, 50, 75, 100])
            ax.set_yticklabels(['25', '50', '75', '100'], size=8)
            ax.set_title('Performance Overview', size=13, fontweight='bold', pad=20)
            ax.grid(True)
            ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1))

            plt.tight_layout()
            buffer = BytesIO()
            plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
            buffer.seek(0)
            plt.close(fig)

            return buffer

        except Exception as e:
            logger.error(f"Error generating radar chart: {e}", exc_info=True)
            plt.close('all')
            return None

    def _generate_histogram(self, user_value: float, all_values: list,
                            title: str, xlabel: str, user_label: str) -> BytesIO:
        """Generate histogram with user position marked"""
        try:
            if not all_values or len(all_values) < 2:
                return None

            fig, ax = plt.subplots(figsize=(6, 3.5))

            # Create histogram
            n, bins, patches = ax.hist(all_values, bins=10, color='#3498DB',
                                       alpha=0.7, edgecolor='black', linewidth=0.5)

            # Mark user position
            user_bin_idx = np.digitize(user_value, bins) - 1
            if 0 <= user_bin_idx < len(patches):
                patches[user_bin_idx].set_facecolor('#F39C12')
                patches[user_bin_idx].set_edgecolor('black')
                patches[user_bin_idx].set_linewidth(2)

            ax.axvline(user_value, color='red', linestyle='--', linewidth=2.5,
                       label=user_label)

            ax.set_xlabel(xlabel, fontsize=11)
            ax.set_ylabel('Number of Users', fontsize=11)
            ax.set_title(title, fontsize=12, fontweight='bold')
            ax.legend(fontsize=9)
            ax.grid(True, alpha=0.3, axis='y')

            plt.tight_layout()
            buffer = BytesIO()
            plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
            buffer.seek(0)
            plt.close(fig)

            return buffer

        except Exception as e:
            logger.error(f"Error generating histogram: {e}", exc_info=True)
            plt.close('all')
            return None

    def _add_proficiency_legend(self, elements):
        """Add Proficiency Levels legend box to PDF"""

        # Section header
        elements.append(Spacer(1, 0.3 * inch))
        elements.append(Paragraph("Proficiency Levels", self.styles['SectionHeader']))
        elements.append(Spacer(1, 0.1 * inch))

        # Legend description
        elements.append(Paragraph(
            "Understanding your theta (θ) score and proficiency level:",
            self.styles['Normal']
        ))
        elements.append(Spacer(1, 0.15 * inch))

        # Create legend table with color-coded proficiency levels
        legend_data = [
            ['Level', 'Theta Range', 'Description'],
            ['Beginner', 'θ < -1.0', 'Foundation building stage - Focus on core concepts'],
            ['Intermediate', '-1.0 ≤ θ < 0.0', 'Developing skills - Building competency'],
            ['Advanced', '0.0 ≤ θ < 1.0', 'Strong proficiency - Mastering concepts'],
            ['Expert', 'θ ≥ 1.0', 'Exceptional mastery - Advanced application'],
        ]

        # Define color coding
        level_colors = {
            'Beginner': colors.HexColor('#EF4444'),  # Red
            'Intermediate': colors.HexColor('#F59E0B'),  # Orange
            'Advanced': colors.HexColor('#10B981'),  # Green
            'Expert': colors.HexColor('#3B82F6'),  # Blue
        }

        legend_table = Table(legend_data, colWidths=[1.2 * inch, 1.3 * inch, 3.5 * inch])

        # Base table style
        table_style = [
            ('FONT', (0, 0), (-1, 0), 'Helvetica-Bold', 10),
            ('FONT', (0, 1), (-1, -1), 'Helvetica', 9),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495E')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ]

        # Add color-coded backgrounds for each proficiency level
        for i, level in enumerate(['Beginner', 'Intermediate', 'Advanced', 'Expert'], start=1):
            bg_color = level_colors[level]
            light_bg = colors.Color(bg_color.red, bg_color.green, bg_color.blue, alpha=0.2)
            table_style.append(('BACKGROUND', (0, i), (0, i), light_bg))
            table_style.append(('TEXTCOLOR', (0, i), (0, i), bg_color))
            table_style.append(('FONT', (0, i), (0, i), 'Helvetica-Bold', 9))

        legend_table.setStyle(TableStyle(table_style))
        elements.append(legend_table)

        # Add note
        elements.append(Spacer(1, 0.15 * inch))
        elements.append(Paragraph(
            "<i>Note: The theta (θ) value is derived from Item Response Theory (IRT) and represents "
            "your ability level on a standardized scale. Higher theta values indicate greater proficiency.</i>",
            self.styles['Normal']
        ))
        elements.append(Spacer(1, 0.2 * inch))
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.grey, spaceAfter=0.2 * inch))

    # Replace the generate_session_pdf method in your PDFExportService class with this:

    def generate_session_pdf(self, session_data: dict, user_data: dict,
                             response_details: list, comparative_data: dict = None) -> BytesIO:
        """Generate comprehensive PDF report for assessment session"""
        from reportlab.platypus import KeepTogether

        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4,
                                rightMargin=0.75 * inch, leftMargin=0.75 * inch,
                                topMargin=0.6 * inch, bottomMargin=0.6 * inch)
        elements = []

        # ========== TITLE ==========
        elements.append(Paragraph("Assessment Report", self.styles['CustomTitle']))
        elements.append(Spacer(1, 0.15 * inch))

        # ========== PROFICIENCY LEGEND ==========
        elements.append(Spacer(1, 0.2 * inch))
        elements.append(Paragraph("Proficiency Levels", self.styles['SectionHeader']))
        elements.append(Spacer(1, 0.08 * inch))

        # Legend description
        elements.append(Paragraph(
            "Understanding your theta (θ) score and proficiency level:",
            self.styles['Normal']
        ))
        elements.append(Spacer(1, 0.1 * inch))

        # Create legend table
        legend_data = [
            ['Level', 'Theta Range', 'Description'],
            ['Beginner', 'θ < -1.0', 'Foundation building - Focus on core concepts'],
            ['Intermediate', '-1.0 ≤ θ < 0.0', 'Developing skills - Building competency'],
            ['Advanced', '0.0 ≤ θ < 1.0', 'Strong proficiency - Mastering concepts'],
            ['Expert', 'θ ≥ 1.0', 'Exceptional mastery - Advanced application'],
        ]

        level_colors = {
            'Beginner': colors.HexColor('#EF4444'),
            'Intermediate': colors.HexColor('#F59E0B'),
            'Advanced': colors.HexColor('#10B981'),
            'Expert': colors.HexColor('#3B82F6'),
        }

        legend_table = Table(legend_data, colWidths=[1.1 * inch, 1.2 * inch, 3.7 * inch])

        # Standardized table style
        table_style = [
            ('FONT', (0, 0), (-1, 0), 'Helvetica-Bold', 10),
            ('FONT', (0, 1), (-1, -1), 'Helvetica', 9),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495E')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ]

        for i, level in enumerate(['Beginner', 'Intermediate', 'Advanced', 'Expert'], start=1):
            bg_color = level_colors[level]
            light_bg = colors.Color(bg_color.red, bg_color.green, bg_color.blue, alpha=0.2)
            table_style.append(('BACKGROUND', (0, i), (0, i), light_bg))
            table_style.append(('TEXTCOLOR', (0, i), (0, i), bg_color))
            table_style.append(('FONT', (0, i), (0, i), 'Helvetica-Bold', 9))

        legend_table.setStyle(TableStyle(table_style))

        # Use KeepTogether to prevent page breaks
        legend_content = [
            Paragraph("Proficiency Levels", self.styles['SectionHeader']),
            Spacer(1, 0.08 * inch),
            Paragraph("Understanding your theta (θ) score and proficiency level:", self.styles['Normal']),
            Spacer(1, 0.1 * inch),
            legend_table,
            Spacer(1, 0.1 * inch),
            Paragraph(
                "<i>Note: Theta (θ) from Item Response Theory represents your ability on a standardized scale.</i>",
                self.styles['Normal']
            )
        ]
        elements.append(KeepTogether(legend_content))
        elements.append(Spacer(1, 0.15 * inch))
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.grey))
        elements.append(Spacer(1, 0.2 * inch))

        # ========== ASSESSMENT OVERVIEW TABLE ==========
        # Format date
        date_str = 'N/A'
        created_at = session_data.get('created_at') or session_data.get('completed_at')
        if created_at:
            try:
                if isinstance(created_at, str):
                    if 'T' in created_at:
                        from datetime import datetime as dt
                        date_obj = dt.fromisoformat(created_at.replace('Z', '+00:00'))
                        date_str = date_obj.strftime('%Y-%m-%d %H:%M')
                    else:
                        date_str = created_at
                else:
                    date_str = created_at.strftime('%Y-%m-%d %H:%M')
            except Exception as e:
                logger.warning(f"Error formatting date: {e}")
                date_str = str(created_at) if created_at else 'N/A'

        session_id = session_data.get('session_id') or session_data.get('id', 'N/A')
        item_bank_name = (session_data.get('item_bank_name') or session_data.get('subject', 'N/A'))
        if item_bank_name != 'N/A':
            item_bank_name = item_bank_name.replace('_', ' ').title()
        status = 'Completed' if session_data.get('completed', True) else 'Active'

        overview_data = [
            ['Field', 'Value'],
            ['User', user_data.get('username', 'N/A')],
            ['Session ID', str(session_id)],
            ['Item Bank', item_bank_name],
            ['Date', date_str],
            ['Status', status],
        ]

        overview_table = Table(overview_data, colWidths=[2 * inch, 4 * inch])
        overview_table.setStyle(TableStyle([
            ('FONT', (0, 0), (-1, 0), 'Helvetica-Bold', 10),
            ('FONT', (0, 1), (0, -1), 'Helvetica-Bold', 9),
            ('FONT', (1, 1), (1, -1), 'Helvetica', 9),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495E')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('TEXTCOLOR', (0, 1), (0, -1), colors.HexColor('#34495E')),
            ('TEXTCOLOR', (1, 1), (1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, 0), 'LEFT'),
            ('ALIGN', (0, 1), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8F9FA')]),
        ]))

        overview_content = [
            Paragraph("Assessment Overview", self.styles['SectionHeader']),
            Spacer(1, 0.08 * inch),
            overview_table
        ]
        elements.append(KeepTogether(overview_content))
        elements.append(Spacer(1, 0.2 * inch))

        # ========== PERFORMANCE SUMMARY TABLE ==========
        theta = session_data.get('theta', 0) or session_data.get('final_theta', 0)

        if theta < -1.0:
            proficiency_level = 'Beginner'
            level_color = colors.HexColor('#EF4444')
            level_bg = colors.Color(0.937, 0.267, 0.267, alpha=0.15)
        elif theta < 0.0:
            proficiency_level = 'Intermediate'
            level_color = colors.HexColor('#F59E0B')
            level_bg = colors.Color(0.961, 0.620, 0.043, alpha=0.15)
        elif theta < 1.0:
            proficiency_level = 'Advanced'
            level_color = colors.HexColor('#10B981')
            level_bg = colors.Color(0.063, 0.725, 0.506, alpha=0.15)
        else:
            proficiency_level = 'Expert'
            level_color = colors.HexColor('#3B82F6')
            level_bg = colors.Color(0.231, 0.510, 0.965, alpha=0.15)

        competence_tier = (session_data.get('competence_tier') or session_data.get('tier', 'N/A'))
        questions_answered = (session_data.get('questions_answered') or
                              session_data.get('questions_asked') or
                              len(response_details) if response_details else 0)

        accuracy = session_data.get('accuracy', 0)
        if accuracy == 0 and response_details:
            correct = sum(1 for r in response_details if r.get('is_correct', False))
            accuracy = correct / len(response_details) if response_details else 0

        performance_data = [
            ['Metric', 'Value'],
            ['Final Theta (θ)', f"{theta:.2f}"],
            ['Proficiency Level', proficiency_level],
            ['Accuracy', f"{accuracy * 100:.1f}%"],
            ['Questions Answered', str(questions_answered)],
            ['Competence Tier', competence_tier],
        ]

        performance_table = Table(performance_data, colWidths=[2.5 * inch, 3.5 * inch])

        perf_style = [
            ('FONT', (0, 0), (-1, 0), 'Helvetica-Bold', 10),
            ('FONT', (0, 1), (0, -1), 'Helvetica-Bold', 9),
            ('FONT', (1, 1), (1, -1), 'Helvetica', 10),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495E')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('TEXTCOLOR', (0, 1), (0, -1), colors.HexColor('#34495E')),
            ('TEXTCOLOR', (1, 1), (1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, 0), 'LEFT'),
            ('ALIGN', (0, 1), (0, -1), 'LEFT'),
            ('ALIGN', (1, 1), (1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8F9FA')]),
        ]

        perf_style.extend([
            ('BACKGROUND', (1, 3), (1, 3), level_bg),
            ('TEXTCOLOR', (1, 3), (1, 3), level_color),
            ('FONT', (1, 3), (1, 3), 'Helvetica-Bold', 10),
        ])

        if competence_tier != 'N/A':
            perf_style.extend([
                ('FONT', (1, 6), (1, 6), 'Helvetica-Bold', 10),
                ('TEXTCOLOR', (1, 6), (1, 6), colors.HexColor('#8E44AD')),
            ])

        performance_table.setStyle(TableStyle(perf_style))

        perf_content = [
            Paragraph("Performance Summary", self.styles['SectionHeader']),
            Spacer(1, 0.08 * inch),
            performance_table
        ]
        elements.append(KeepTogether(perf_content))

        # ========== THETA PROGRESSION CHART ==========
        elements.append(PageBreak())
        elements.append(Paragraph("θ Progression", self.styles['SectionHeader']))
        elements.append(Spacer(1, 0.1 * inch))

        responses_with_data = []
        for resp in response_details:
            responses_with_data.append({
                'is_correct': resp.get('is_correct', False),
                'theta_after': resp.get('theta_after', theta)
            })

        theta_chart = self._generate_theta_progression_chart(responses_with_data)
        if theta_chart:
            elements.append(Image(theta_chart, width=6.5 * inch, height=3.2 * inch))
        else:
            elements.append(Paragraph("Chart data not available.", self.styles['Normal']))

        elements.append(Spacer(1, 0.2 * inch))

        # ========== TOPIC PERFORMANCE ==========
        topic_performance = session_data.get('topic_performance')
        if topic_performance:
            elements.append(PageBreak())
            elements.append(Paragraph("Topic-wise Performance", self.styles['SectionHeader']))
            elements.append(Spacer(1, 0.1 * inch))

            # Radar chart
            radar_chart = self._generate_topic_radar(topic_performance)
            if radar_chart:
                elements.append(Image(radar_chart, width=5.5 * inch, height=5.5 * inch))

            elements.append(Spacer(1, 0.2 * inch))

            # Topic table
            topic_headers = ['Topic', 'Accuracy', 'Questions', 'Theta', 'Strength']
            topic_data = [topic_headers]

            for topic, perf in topic_performance.items():
                topic_display = topic.replace('Complex Numbers - ', '').replace('complex numbers - ', '')
                if len(topic_display) > 35:
                    topic_display = topic_display[:32] + '...'

                topic_data.append([
                    topic_display.capitalize(),
                    f"{perf.get('accuracy', 0) * 100:.0f}%",
                    str(perf.get('questions_answered', 0)),
                    f"{perf.get('theta', 0):.2f}",
                    perf.get('strength_level', 'N/A')
                ])

            topic_table = Table(topic_data, colWidths=[2.5 * inch, 0.8 * inch, 0.8 * inch, 0.7 * inch, 1.2 * inch])
            topic_table.setStyle(TableStyle([
                ('FONT', (0, 0), (-1, 0), 'Helvetica-Bold', 10),
                ('FONT', (0, 1), (-1, -1), 'Helvetica', 9),
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495E')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (0, -1), 'LEFT'),
                ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8F9FA')]),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ]))
            elements.append(topic_table)

        # ========== LEARNING ROADMAP ==========
        learning_roadmap = session_data.get('learning_roadmap')
        if learning_roadmap:
            elements.append(PageBreak())
            elements.append(Paragraph("Personalized Learning Roadmap", self.styles['SectionHeader']))
            elements.append(Spacer(1, 0.1 * inch))

            elements.append(Paragraph(learning_roadmap.get('overall_message', ''), self.styles['Normal']))
            elements.append(Spacer(1, 0.2 * inch))

            for rec in learning_roadmap.get('recommendations', []):
                title_text = rec['title']
                if rec['type'] == 'immediate_focus':
                    title_text = "🎯 " + title_text
                elif rec['type'] == 'practice_more':
                    title_text = "💡 " + title_text
                elif rec['type'] == 'maintain':
                    title_text = "✓ " + title_text

                title_color = {
                    'immediate_focus': '#E74C3C',
                    'practice_more': '#F39C12',
                    'maintain': '#27AE60'
                }.get(rec['type'], '#34495E')

                rec_title_style = ParagraphStyle(
                    'RecTitle',
                    parent=self.styles['Subsection'],
                    textColor=colors.HexColor(title_color),
                    fontSize=12
                )

                rec_content = [
                    Paragraph(title_text, rec_title_style),
                    Spacer(1, 0.05 * inch),
                    Paragraph(rec['description'], self.styles['Normal']),
                    Spacer(1, 0.05 * inch),
                    Paragraph("<b>Topics:</b> " + ", ".join(
                        [t.replace('Complex Numbers - ', '').replace('complex numbers - ', '') for t in rec['topics']]),
                              self.styles['Normal']),
                    Paragraph(f"<b>💡 {rec['action']}</b>", self.styles['Normal']),
                    Spacer(1, 0.15 * inch)
                ]
                elements.extend(rec_content)

        # ========== QUESTION DETAILS ==========
        if response_details:
            elements.append(PageBreak())
            elements.append(Paragraph("Question Response Details", self.styles['SectionHeader']))
            elements.append(Spacer(1, 0.1 * inch))

            resp_headers = ['#', 'Question', 'Your Answer', 'Correct', 'Result']
            resp_data = [resp_headers]

            for i, resp in enumerate(response_details, 1):
                question = self._sanitize_text(resp['question'])
                question = question[:60] + '...' if len(question) > 60 else question

                resp_data.append([
                    str(i),
                    question,
                    resp['selected_option'],
                    resp['correct_answer'],
                    '✓' if resp['is_correct'] else '✗'
                ])

            resp_table = Table(resp_data, colWidths=[0.4 * inch, 3.2 * inch, 0.9 * inch, 0.9 * inch, 0.6 * inch])

            table_font = self.unicode_font if hasattr(self, 'unicode_font') else 'Helvetica'
            table_font_bold = self.unicode_font_bold if hasattr(self, 'unicode_font_bold') else 'Helvetica-Bold'

            resp_table.setStyle(TableStyle([
                ('FONT', (0, 0), (-1, 0), table_font_bold, 10),
                ('FONT', (0, 1), (-1, -1), table_font, 8),
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495E')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (0, -1), 'CENTER'),
                ('ALIGN', (2, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8F9FA')]),
                ('TOPPADDING', (0, 0), (-1, -1), 5),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ]))

            for i, resp in enumerate(response_details, 1):
                if resp['is_correct']:
                    resp_table.setStyle(TableStyle([
                        ('TEXTCOLOR', (4, i), (4, i), colors.green),
                        ('FONT', (4, i), (4, i), 'Helvetica-Bold', 11),
                    ]))
                else:
                    resp_table.setStyle(TableStyle([
                        ('TEXTCOLOR', (4, i), (4, i), colors.red),
                        ('FONT', (4, i), (4, i), 'Helvetica-Bold', 11),
                    ]))

            elements.append(resp_table)

        # ========== FOOTER ==========
        elements.append(Spacer(1, 0.3 * inch))
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.grey))
        elements.append(Spacer(1, 0.08 * inch))
        footer = Paragraph(
            f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            self.styles['Normal']
        )
        footer.alignment = TA_CENTER
        elements.append(footer)

        # Build PDF
        doc.build(elements)
        buffer.seek(0)
        return buffer

    # Add these TWO new methods to your PDFExportService class in services.py
    # Place them AFTER the existing generate_session_pdf() method

    def export_complete_session(self, registry_db: Session, item_db: Session,
                                session_id: int, item_bank_name: str) -> BytesIO:
        """
        Export complete session data as PDF - ALL business logic here

        This method replaces the logic that was in main.py
        """
        # 1. Get session
        session = item_db.query(models_itembank.AssessmentSession).filter(
            models_itembank.AssessmentSession.session_id == session_id
        ).first()

        if not session:
            raise ValueError(f"Session {session_id} not found")

        # 2. Get user
        user = registry_db.query(models_registry.User).filter(
            models_registry.User.id == session.user_id
        ).first()

        if not user:
            raise ValueError(f"User with ID {session.user_id} not found")

        # 3. Get responses
        responses = item_db.query(models_itembank.Response).filter(
            models_itembank.Response.session_id == session_id
        ).order_by(models_itembank.Response.created_at).all()

        # 4. Calculate stats
        correct_count = sum(1 for r in responses if r.is_correct)
        accuracy = correct_count / len(responses) if responses else 0

        # 5. Prepare session data
        session_data = {
            'session_id': session.session_id,
            'subject': session.subject,
            'item_bank_name': item_bank_name,
            'theta': session.theta,
            'sem': session.sem,
            'tier': session.tier,
            'competence_tier': session.tier,
            'questions_asked': session.questions_asked,
            'questions_answered': session.questions_asked,
            'completed': session.completed,
            'created_at': session.started_at,
            'started_at': session.started_at,
            'completed_at': session.completed_at,
            'correct_count': correct_count,
            'accuracy': accuracy,
            'status': 'Completed' if session.completed else 'Active'
        }

        # 6. Get/calculate topic performance
        topic_perf = None
        try:
            if hasattr(session, 'topic_performance') and session.topic_performance:
                topic_perf = json.loads(session.topic_performance) if isinstance(
                    session.topic_performance, str
                ) else session.topic_performance
                logger.info(f"Loaded topic performance: {len(topic_perf)} topics")

            if not topic_perf:
                logger.info("Calculating topic performance from responses...")
                topic_perf = self._calculate_topic_performance_for_export(item_db, responses)

            if topic_perf:
                session_data['topic_performance'] = topic_perf
                roadmap = TopicPerformanceCalculator.generate_learning_roadmap(
                    topic_perf, session.theta
                )
                if roadmap:
                    session_data['learning_roadmap'] = roadmap

        except Exception as e:
            logger.error(f"Error with topic performance: {e}", exc_info=True)

        # 7. User data
        user_data = {
            'username': user.username,
            'id': user.id
        }

        # 8. Response details
        response_details = []
        for resp in responses:
            question = item_db.query(models_itembank.Question).filter(
                models_itembank.Question.id == resp.question_id
            ).first()

            if question:
                response_details.append({
                    'question': question.question,
                    'selected_option': resp.selected_option,
                    'correct_answer': question.answer,
                    'is_correct': resp.is_correct,
                    'theta_after': resp.theta_after,
                    'difficulty': question.difficulty_b,
                    'topic': question.topic if hasattr(question, 'topic') else None
                })

        # 9. Generate PDF
        return self.generate_session_pdf(
            session_data, user_data, response_details, comparative_data=None
        )

    def _calculate_topic_performance_for_export(self, item_db: Session,
                                                responses: List) -> Optional[Dict]:
        """Helper: Calculate topic performance from responses"""
        try:
            topic_calculator = TopicPerformanceCalculator()
            irt_engine = IRTEngine()
            topic_data = defaultdict(list)

            for resp in responses:
                question = item_db.query(models_itembank.Question).filter(
                    models_itembank.Question.id == resp.question_id
                ).first()

                if question and question.topic:
                    topic_data[question.topic].append({
                        'is_correct': resp.is_correct,
                        'difficulty': question.difficulty_b,
                        'discrimination': question.discrimination_a,
                        'guessing': question.guessing_c,
                        'topic': question.topic
                    })

            topic_performance = {}
            for topic, data in topic_data.items():
                perf = topic_calculator.calculate_topic_theta(data, topic, irt_engine)
                if perf:
                    topic_performance[topic] = perf

            return topic_performance if topic_performance else None

        except Exception as e:
            logger.error(f"Error calculating topic performance: {e}", exc_info=True)
            return None

# ========== NEW CLASS - Session Management Service ==========

class SessionManagementService:
    """NEW: Service for managing assessment sessions"""

    def __init__(self):
        self.user_service = UserService()
        self.irt_engine = IRTEngine()

    def terminate_single_session(self, item_db: Session, registry_db: Session,
                                 session_id: int, item_bank_name: str) -> Dict:
        """Terminate a specific assessment session"""
        try:
            # Get the session
            session = item_db.query(models_itembank.AssessmentSession).filter(
                models_itembank.AssessmentSession.session_id == session_id
            ).first()

            if not session:
                return {
                    'success': False,
                    'error': f'Session {session_id} not found'
                }

            if session.completed:
                return {
                    'success': False,
                    'error': f'Session {session_id} is already completed'
                }

            # Calculate final statistics
            responses = item_db.query(models_itembank.Response).filter(
                models_itembank.Response.session_id == session_id
            ).all()

            # Mark session as completed
            session.completed = True
            session.completed_at = datetime.utcnow()

            # Update user proficiency if there are responses
            if responses:
                # Calculate topic performance
                topic_performance = self._calculate_topic_performance(item_db, responses)

                # Update user proficiency
                self.user_service.update_user_proficiency(
                    registry_db, item_db,
                    session.user_id, item_bank_name, session.subject,
                    session.theta, session.sem, session.tier,
                    topic_performance
                )

            item_db.commit()

            return {
                'success': True,
                'message': f'Session {session_id} terminated successfully',
                'session_id': session_id,
                'questions_answered': session.questions_asked,
                'final_theta': session.theta,
                'final_tier': session.tier
            }

        except Exception as e:
            item_db.rollback()
            logger.error(f"Error terminating session {session_id}: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def terminate_all_active_sessions(self, registry_db: Session) -> Dict:
        """Terminate all active sessions across all item banks"""
        terminated_sessions = []
        errors = []

        # Get all item banks
        item_banks = registry_db.query(models_registry.ItemBank).all()

        for item_bank in item_banks:
            item_db = item_bank_db.get_session(item_bank.name)
            try:
                # Find all active sessions in this item bank
                active_sessions = item_db.query(models_itembank.AssessmentSession).filter(
                    models_itembank.AssessmentSession.completed == False
                ).all()

                for session in active_sessions:
                    result = self.terminate_single_session(
                        item_db, registry_db,
                        session.session_id, item_bank.name
                    )

                    if result['success']:
                        terminated_sessions.append({
                            'item_bank': item_bank.name,
                            'session_id': session.session_id,
                            'user_id': session.user_id
                        })
                    else:
                        errors.append({
                            'item_bank': item_bank.name,
                            'session_id': session.session_id,
                            'error': result['error']
                        })

            except Exception as e:
                logger.error(f"Error processing item bank {item_bank.name}: {e}")
                errors.append({
                    'item_bank': item_bank.name,
                    'error': str(e)
                })
            finally:
                item_db.close()

        return {
            'success': len(errors) == 0,
            'terminated_count': len(terminated_sessions),
            'terminated_sessions': terminated_sessions,
            'errors': errors if errors else None,
            'message': f'Terminated {len(terminated_sessions)} active sessions'
        }

    def terminate_item_bank_sessions(self, item_db: Session, registry_db: Session,
                                     item_bank_name: str) -> Dict:
        """Terminate all active sessions for a specific item bank"""
        try:
            # Find all active sessions
            active_sessions = item_db.query(models_itembank.AssessmentSession).filter(
                models_itembank.AssessmentSession.completed == False
            ).all()

            terminated_sessions = []
            errors = []

            for session in active_sessions:
                result = self.terminate_single_session(
                    item_db, registry_db,
                    session.session_id, item_bank_name
                )

                if result['success']:
                    terminated_sessions.append({
                        'session_id': session.session_id,
                        'user_id': session.user_id,
                        'questions_answered': result['questions_answered']
                    })
                else:
                    errors.append({
                        'session_id': session.session_id,
                        'error': result['error']
                    })

            return {
                'success': len(errors) == 0,
                'item_bank': item_bank_name,
                'terminated_count': len(terminated_sessions),
                'terminated_sessions': terminated_sessions,
                'errors': errors if errors else None,
                'message': f'Terminated {len(terminated_sessions)} sessions in {item_bank_name}'
            }

        except Exception as e:
            logger.error(f"Error terminating sessions for {item_bank_name}: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def _calculate_topic_performance(self, db: Session, responses: List) -> Optional[Dict]:
        """Calculate topic performance for responses"""
        try:
            topic_calculator = TopicPerformanceCalculator()
            question_service = QuestionService()

            topic_data = defaultdict(list)

            for resp in responses:
                question = question_service.get_question_by_id(db, resp.question_id)
                if question and question.topic:
                    topic_data[question.topic].append({
                        'is_correct': resp.is_correct,
                        'difficulty': question.difficulty_b,
                        'discrimination': question.discrimination_a,
                        'guessing': question.guessing_c,
                        'topic': question.topic
                    })

            topic_performance = {}
            for topic, data in topic_data.items():
                perf = topic_calculator.calculate_topic_theta(data, topic, self.irt_engine)
                if perf:
                    topic_performance[topic] = perf

            return topic_performance if topic_performance else None

        except Exception as e:
            logger.debug(f"Could not calculate topic performance: {e}")
            return None

# ========== UNCHANGED CLASSES - All original methods preserved ==========

class UserService:
    """BACKWARD COMPATIBLE - All original methods unchanged"""

    def get_or_create_user(self, db: Session, username: str,
                           initial_competence_level: str = "beginner") -> models_registry.User:
        """UNCHANGED"""
        user = db.query(models_registry.User).filter(
            models_registry.User.username == username
        ).first()

        if not user:
            user = models_registry.User(
                username=username,
                initial_competence_level=initial_competence_level
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        return user

    def get_user_by_username(self, db: Session, username: str) -> Optional[models_registry.User]:
        """UNCHANGED"""
        return db.query(models_registry.User).filter(
            models_registry.User.username == username
        ).first()

    def get_user_proficiency(self, db: Session, user_id: int) -> schemas.UserProficiency:
        """UNCHANGED"""
        user = db.query(models_registry.User).filter(
            models_registry.User.id == user_id
        ).first()

        proficiencies = db.query(models_registry.UserProficiencySummary).filter(
            models_registry.UserProficiencySummary.user_id == user_id
        ).all()

        proficiency_list = []
        for prof in proficiencies:
            proficiency_list.append(schemas.UserProficiencySubject(
                item_bank=prof.item_bank_name,
                subject=prof.subject,
                theta=prof.theta,
                sem=prof.sem,
                tier=prof.tier,
                assessments_taken=prof.assessments_taken,
                last_updated=prof.last_updated
            ))

        return schemas.UserProficiency(
            username=user.username,
            proficiencies=proficiency_list
        )

    def update_user_proficiency(self, registry_db: Session, item_db: Session,
                                user_id: int, item_bank_name: str, subject: str,
                                theta: float, sem: float, tier: str,
                                topic_performance: Dict = None):
        """ENHANCED but BACKWARD COMPATIBLE - topic_performance is OPTIONAL"""

        proficiency = item_db.query(models_itembank.UserProficiency).filter(
            and_(
                models_itembank.UserProficiency.user_id == user_id,
                models_itembank.UserProficiency.subject == subject
            )
        ).first()

        if proficiency:
            proficiency.theta = theta
            proficiency.sem = sem
            proficiency.tier = tier
            proficiency.assessments_taken += 1
            # NEW: Only set if column exists and data provided
            if topic_performance:
                try:
                    if hasattr(proficiency, 'topic_performance'):
                        proficiency.topic_performance = json.dumps(topic_performance)
                except Exception as e:
                    logger.debug(f"Could not save topic performance: {e}")
        else:
            prof_data = {
                'user_id': user_id,
                'subject': subject,
                'theta': theta,
                'sem': sem,
                'tier': tier,
                'assessments_taken': 1
            }
            # NEW: Only add if we have the data
            if topic_performance:
                try:
                    prof_data['topic_performance'] = json.dumps(topic_performance)
                except Exception as e:
                    logger.debug(f"Could not add topic performance: {e}")

            proficiency = models_itembank.UserProficiency(**prof_data)
            item_db.add(proficiency)

        item_db.commit()

        # Original cache update preserved
        cache = registry_db.query(models_registry.UserProficiencySummary).filter(
            and_(
                models_registry.UserProficiencySummary.user_id == user_id,
                models_registry.UserProficiencySummary.item_bank_name == item_bank_name
            )
        ).first()

        if cache:
            cache.theta = theta
            cache.sem = sem
            cache.tier = tier
            cache.assessments_taken = proficiency.assessments_taken
            cache.last_updated = datetime.utcnow()

            # REGISTRY_CACHE_ENHANCEMENT: Cache topic performance in registry for faster dashboard loading
            if topic_performance:
                try:
                    if hasattr(cache, 'topic_performance'):
                        cache.topic_performance = json.dumps(topic_performance)
                        logger.debug(f"Cached topic performance in registry for user {user_id}")
                except Exception as e:
                    logger.debug(f"Could not cache topic performance in registry: {e}")
        else:
            cache_data = {
                'user_id': user_id,
                'item_bank_name': item_bank_name,
                'subject': subject,
                'theta': theta,
                'sem': sem,
                'tier': tier,
                'assessments_taken': proficiency.assessments_taken
            }

            # REGISTRY_CACHE_ENHANCEMENT: Include topic performance in new cache entry
            if topic_performance:
                try:
                    cache_data['topic_performance'] = json.dumps(topic_performance)
                    logger.debug(f"Created registry cache with topic performance for user {user_id}")
                except Exception as e:
                    logger.debug(f"Could not add topic performance to registry cache: {e}")

            cache = models_registry.UserProficiencySummary(**cache_data)
            registry_db.add(cache)

        registry_db.commit()
        logger.info(f"Updated proficiency for user {user_id}")
class QuestionService:
    """UNCHANGED - All original methods preserved"""

    def import_questions_from_df(self, db: Session, df: pd.DataFrame) -> int:
        """UNCHANGED"""
        imported_count = 0

        for _, row in df.iterrows():
            existing = db.query(models_itembank.Question).filter(
                models_itembank.Question.question_id == row['question_id']
            ).first()

            if not existing:
                question = models_itembank.Question(
                    subject=row['subject'],
                    question_id=row['question_id'],
                    question=row['question'],
                    option_a=row['option_a'],
                    option_b=row['option_b'],
                    option_c=row['option_c'],
                    option_d=row['option_d'],
                    answer=row['answer'],
                    topic=row['topic'],
                    content_area=row.get('content_area', row['topic']),
                    tier=row['tier'],
                    discrimination_a=float(row['discrimination_a']),
                    difficulty_b=float(row['difficulty_b']),
                    guessing_c=float(row['guessing_c'])
                )
                db.add(question)
                imported_count += 1

        db.commit()
        return imported_count

    def get_available_questions(self, db: Session, session_id: int, subject: str) -> List[Dict]:
        """UNCHANGED"""
        asked_question_ids = db.query(models_itembank.Response.question_id).filter(
            models_itembank.Response.session_id == session_id
        ).scalar_subquery()

        questions = db.query(models_itembank.Question).filter(
            and_(
                models_itembank.Question.subject == subject,
                not_(models_itembank.Question.id.in_(asked_question_ids))
            )
        ).all()

        return [
            {
                'id': q.id,
                'question_id': q.question_id,
                'question': q.question,
                'option_a': q.option_a,
                'option_b': q.option_b,
                'option_c': q.option_c,
                'option_d': q.option_d,
                'answer': q.answer,
                'topic': q.topic,
                'content_area': q.content_area or q.topic,
                'tier': q.tier,
                'discrimination_a': q.discrimination_a,
                'difficulty_b': q.difficulty_b,
                'guessing_c': q.guessing_c
            }
            for q in questions
        ]

    def get_question_by_id(self, db: Session, question_id: int) -> Optional[models_itembank.Question]:
        """UNCHANGED"""
        return db.query(models_itembank.Question).filter(
            models_itembank.Question.id == question_id
        ).first()


class AssessmentService:
    """ENHANCED but BACKWARD COMPATIBLE - All original methods work"""

    def __init__(self):
        self.user_service = UserService()
        self.question_service = QuestionService()
        self.topic_calculator = TopicPerformanceCalculator()

    def start_assessment(self, item_db: Session, registry_db: Session,
                         user_id: int, subject: str, item_bank_name: str) -> models_itembank.AssessmentSession:
        """UNCHANGED"""
        logger.info(f"Start assessment for user {user_id} in item bank {item_bank_name}")

        user_proficiency = item_db.query(models_itembank.UserProficiency).filter(
            and_(
                models_itembank.UserProficiency.user_id == user_id,
                models_itembank.UserProficiency.subject == subject
            )
        ).first()

        if user_proficiency:
            starting_theta = user_proficiency.theta
            logger.info(f"Using existing proficiency theta: {starting_theta:.3f}")
        else:
            user = registry_db.query(models_registry.User).filter(
                models_registry.User.id == user_id
            ).first()
            irt_engine = IRTEngine()
            starting_theta = irt_engine.get_initial_theta(user.initial_competence_level)
            logger.info(f"Using initial competence: {user.initial_competence_level}, theta: {starting_theta:.3f}")

        session = models_itembank.AssessmentSession(
            user_id=user_id,
            subject=subject,
            theta=starting_theta,
            sem=1.0,
            tier=IRTEngine().theta_to_tier(starting_theta),
            questions_asked=0,
            completed=False
        )

        item_db.add(session)
        item_db.commit()
        item_db.refresh(session)

        logger.info(f"Assessment session created successfully")
        return session

    def get_session(self, db: Session, session_id: int) -> Optional[models_itembank.AssessmentSession]:
        """UNCHANGED"""
        return db.query(models_itembank.AssessmentSession).filter(
            models_itembank.AssessmentSession.session_id == session_id
        ).first()

    def get_next_question(self, db: Session, session_id: int,
                          irt_engine: IRTEngine) -> Optional[schemas.QuestionResponse]:
        """UNCHANGED"""
        session = self.get_session(db, session_id)
        if not session or session.completed:
            return None

        responses = db.query(models_itembank.Response).filter(
            models_itembank.Response.session_id == session_id
        ).order_by(models_itembank.Response.created_at).all()

        response_history = [r.is_correct for r in responses]

        available_questions = self.question_service.get_available_questions(
            db, session_id, session.subject
        )

        if not available_questions:
            session.completed = True
            session.completed_at = datetime.utcnow()
            db.commit()
            return None

        next_question_data = irt_engine.select_next_question(
            session.theta,
            available_questions,
            response_history,
            session.questions_asked
        )

        if not next_question_data:
            return None

        logger.info(f"Selected question: {next_question_data['question_id']}")

        return schemas.QuestionResponse(
            id=next_question_data['id'],
            question=next_question_data['question'],
            option_a=next_question_data['option_a'],
            option_b=next_question_data['option_b'],
            option_c=next_question_data['option_c'],
            option_d=next_question_data['option_d'],
            topic=next_question_data['topic'],
            tier=next_question_data['tier'],
            difficulty_b=next_question_data['difficulty_b'],
            discrimination_a=next_question_data['discrimination_a'],
            guessing_c=next_question_data['guessing_c']
        )

    # This shows the key modifications to the record_response method

    # MODIFIED: record_response method in AssessmentService class
    # CHANGE: Now returns dict with 'response' and 'topic_performance' instead of just response

    def record_response(self, item_db: Session, registry_db: Session,
                        session_id: int, question_id: int, selected_option: str,
                        item_bank_name: str, irt_engine: IRTEngine):
        """ENHANCED but BACKWARD COMPATIBLE"""
        session = self.get_session(item_db, session_id)
        question = self.question_service.get_question_by_id(item_db, question_id)

        if not session or not question:
            return None  # Changed from return to return None

        is_correct = self.is_answer_correct(selected_option, question.answer)

        # EXISTING: Get all previous responses
        previous_responses = item_db.query(models_itembank.Response).filter(
            models_itembank.Response.session_id == session_id
        ).order_by(models_itembank.Response.created_at).all()

        response_data = []
        for r in previous_responses:
            q = self.question_service.get_question_by_id(item_db, r.question_id)
            response_data.append((r.is_correct, q.difficulty_b, q.discrimination_a, q.guessing_c))

        response_data.append((is_correct, question.difficulty_b, question.discrimination_a, question.guessing_c))
        response_history = [r.is_correct for r in previous_responses] + [is_correct]

        theta_before = session.theta
        new_theta, adjustment_info = irt_engine.update_theta(
            theta_before,
            response_data,
            response_history,
            questions_answered=session.questions_asked
        )

        questions_info = [(r[1], r[2], r[3]) for r in response_data]
        new_sem = irt_engine.calculate_sem(new_theta, questions_info)

        # EXISTING: Create response with safety
        response_dict = {
            'session_id': session_id,
            'question_id': question_id,
            'selected_option': selected_option,
            'is_correct': is_correct,
            'theta_before': theta_before,
            'theta_after': new_theta,
            'sem_after': new_sem
        }

        # EXISTING: Add topic if column exists
        try:
            if hasattr(models_itembank.Response, 'topic'):
                response_dict['topic'] = question.topic
        except Exception as e:
            logger.debug(f"Topic field not available: {e}")

        response = models_itembank.Response(**response_dict)
        item_db.add(response)

        # EXISTING: Update session
        session.theta = new_theta
        session.sem = new_sem
        session.tier = irt_engine.theta_to_tier(new_theta)
        session.questions_asked += 1

        # ENHANCED: Calculate topic performance EVERY TIME (with safety)
        topic_performance = None
        try:
            if hasattr(session, 'topic_performance'):
                all_responses = previous_responses + [response]
                topic_performance = self.calculate_session_topic_performance(
                    item_db, all_responses, irt_engine
                )
                if topic_performance:
                    session.topic_performance = json.dumps(topic_performance)
                    logger.info(f"Topic performance calculated: {len(topic_performance)} topics")
        except Exception as e:
            logger.warning(f"Could not calculate topic performance: {e}")

        # EXISTING: Check completion
        if irt_engine.should_stop_assessment(new_sem, session.questions_asked, response_history):
            session.completed = True
            session.completed_at = datetime.utcnow()

            # NEW: Save detailed topic performance on completion
            if topic_performance:
                try:
                    self.save_topic_performance(item_db, session_id, session.user_id, topic_performance)
                    logger.info(f"Detailed topic performance saved for session {session_id}")
                except Exception as e:
                    logger.warning(f"Could not save detailed topic performance: {e}")

            # EXISTING: Update proficiency
            self.user_service.update_user_proficiency(
                registry_db, item_db,
                session.user_id, item_bank_name, session.subject,
                new_theta, new_sem, irt_engine.theta_to_tier(new_theta),
                topic_performance  # This was already optional
            )

        item_db.commit()

        # CRITICAL CHANGE: Return dict instead of just response
        return {
            'response': response,
            'topic_performance': topic_performance
        }

    # The get_assessment_results method already has the logic to include topic_performance
    # and learning_roadmap - it just needs the data to be available in the session
    # No changes needed to get_assessment_results - it's already prepared for this data

    def calculate_session_topic_performance(self, db: Session, responses: List,
                                            irt_engine: IRTEngine) -> Optional[Dict]:
        """NEW: Calculate performance for each topic"""
        try:
            topic_data = defaultdict(lambda: {
                'responses': [],
                'correct': 0,
                'total': 0
            })

            for resp in responses:
                question = self.question_service.get_question_by_id(db, resp.question_id)
                if question and question.topic:
                    topic = question.topic
                    topic_data[topic]['responses'].append({
                        'is_correct': resp.is_correct,
                        'difficulty': question.difficulty_b,
                        'discrimination': question.discrimination_a,
                        'guessing': question.guessing_c,
                        'topic': topic
                    })
                    topic_data[topic]['total'] += 1
                    if resp.is_correct:
                        topic_data[topic]['correct'] += 1

            topic_performance = {}
            for topic, data in topic_data.items():
                if data['total'] > 0:
                    perf = self.topic_calculator.calculate_topic_theta(
                        data['responses'], topic, irt_engine
                    )
                    if perf:
                        topic_performance[topic] = perf

            return topic_performance if topic_performance else None
        except Exception as e:
            logger.debug(f"Could not calculate topic performance: {e}")
            return None

    def save_topic_performance(self, db: Session, session_id: int,
                               user_id: int, topic_performance: Dict):
        """NEW: Save detailed topic performance records"""
        try:
            for topic, perf in topic_performance.items():
                topic_record = models_itembank.TopicPerformance(
                    session_id=session_id,
                    user_id=user_id,
                    topic=topic,
                    theta=perf['theta'],
                    sem=perf['sem'],
                    questions_answered=perf['questions_answered'],
                    correct_count=perf['correct_count'],
                    accuracy=perf['accuracy'],
                    tier=perf['tier']
                )
                db.add(topic_record)
            db.commit()
        except Exception as e:
            logger.debug(f"Could not save detailed topic performance: {e}")
            db.rollback()

    def get_assessment_results(self, db: Session, session_id: int) -> schemas.AssessmentResults:
        """ENHANCED but BACKWARD COMPATIBLE"""
        session = self.get_session(db, session_id)
        responses = db.query(models_itembank.Response).filter(
            models_itembank.Response.session_id == session_id
        ).order_by(models_itembank.Response.created_at).all()

        correct_count = sum(1 for r in responses if r.is_correct)
        accuracy = correct_count / len(responses) if responses else 0.0

        response_details = []
        for resp in responses:
            question = self.question_service.get_question_by_id(db, resp.question_id)
            detail_dict = {
                'question_id': resp.question_id,
                'question': question.question,
                'selected_option': resp.selected_option,
                'correct_answer': question.answer,
                'is_correct': resp.is_correct,
                'theta_before': resp.theta_before,
                'theta_after': resp.theta_after,
                'difficulty': question.difficulty_b
            }
            # NEW: Add topic if available
            try:
                if hasattr(resp, 'topic') and resp.topic:
                    detail_dict['topic'] = resp.topic
            except:
                pass

            response_details.append(schemas.ResponseDetails(**detail_dict))

        irt_engine = IRTEngine()
        final_tier = irt_engine.theta_to_tier(session.theta)

        # Base result (always available)
        result_dict = {
            'session_id': session.session_id,
            'user_id': session.user_id,
            'subject': session.subject,
            'final_theta': session.theta,
            'final_sem': session.sem,
            'tier': final_tier,
            'questions_asked': session.questions_asked,
            'correct_answers': correct_count,
            'accuracy': accuracy,
            'responses': response_details,
            'completed_at': session.completed_at
        }

        # NEW: Add enhanced data if available
        try:
            if hasattr(session, 'topic_performance') and session.topic_performance:
                topic_perf = json.loads(session.topic_performance) if isinstance(session.topic_performance,
                                                                                 str) else session.topic_performance
                if topic_perf:
                    result_dict['topic_performance'] = topic_perf
                    roadmap = self.topic_calculator.generate_learning_roadmap(
                        topic_perf, session.theta
                    )
                    if roadmap:
                        result_dict['learning_roadmap'] = roadmap
        except Exception as e:
            logger.debug(f"Enhanced results not available: {e}")


        return schemas.AssessmentResults(**result_dict)

    def is_answer_correct(self, selected: str, correct: str) -> bool:
        """UNCHANGED"""
        if not selected or not correct:
            return False
        return str(selected).strip().upper() == str(correct).strip().upper()


class ItemBankService:
    """UNCHANGED - Original service preserved"""

    def __init__(self):
        self.question_service = QuestionService()

    def create_item_bank(self, db: Session, name: str, display_name: str,
                         subject: str) -> models_registry.ItemBank:
        """UNCHANGED"""
        item_bank = models_registry.ItemBank(
            name=name,
            display_name=display_name,
            subject=subject,
            status="pending"
        )
        db.add(item_bank)
        db.commit()
        db.refresh(item_bank)

        item_bank_db.get_engine(name)
        logger.info(f"Created item bank: {name} at {item_bank_db.get_db_path(name)}")

        return item_bank

    def upload_and_calibrate(self, item_bank_name: str, df: pd.DataFrame) -> Dict:
        """Upload questions to item bank - ALWAYS use item_bank_name as subject"""

        item_db = item_bank_db.get_session(item_bank_name)

        try:
            # Validate required columns (don't require 'subject' in CSV anymore)
            required = ['question', 'option_a', 'option_b', 'option_c', 'option_d',
                        'answer', 'tier', 'topic']
            missing = [col for col in required if col not in df.columns]

            if missing:
                return {
                    'success': False,
                    'error': f'Missing required columns: {missing}'
                }

            # CRITICAL: Always override subject with item_bank_name
            # This ensures questions match what the assessment system expects
            df['subject'] = item_bank_name

            # Generate question_id if not provided
            if 'question_id' not in df.columns:
                df['question_id'] = [f"{item_bank_name}_{i + 1}" for i in range(len(df))]

            # Set defaults for IRT parameters if not provided
            if 'content_area' not in df.columns:
                df['content_area'] = df['topic']

            if 'discrimination_a' not in df.columns:
                df['discrimination_a'] = 1.5

            if 'difficulty_b' not in df.columns:
                tier_difficulty_map = {
                    'C1': -1.5,
                    'C2': -0.5,
                    'C3': 0.5,
                    'C4': 1.5
                }
                df['difficulty_b'] = df['tier'].map(tier_difficulty_map).fillna(0.0)

            if 'guessing_c' not in df.columns:
                df['guessing_c'] = 0.25

            # Import questions
            imported = self.question_service.import_questions_from_df(item_db, df)

            logger.info(f"Imported {imported} questions to item bank: {item_bank_name}")

            return {
                'success': True,
                'imported': imported,
                'total_items': imported,
                'message': f'Successfully imported {imported} questions'
            }

        except Exception as e:
            logger.error(f"Error importing to item bank {item_bank_name}: {e}")
            item_db.rollback()
            return {
                'success': False,
                'error': str(e)
            }
        finally:
            item_db.close()


    def get_item_bank_stats(self, item_bank_name: str) -> Dict:
        """UNCHANGED"""


        db_path = item_bank_db.get_db_path(item_bank_name)

        if not os.path.exists(db_path):
            return {
                'total_items': 0,
                'test_takers': 0,
                'total_responses': 0,
                'accuracy': None
            }

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        try:
            cursor.execute("SELECT COUNT(*) FROM questions")
            total_items = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(DISTINCT session_id) FROM assessment_sessions WHERE completed = 1")
            test_takers = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM responses")
            total_responses = cursor.fetchone()[0]

            cursor.execute("SELECT AVG(is_correct) FROM responses")
            accuracy_result = cursor.fetchone()
            accuracy = accuracy_result[0] if accuracy_result[0] is not None else None

            return {
                'total_items': total_items,
                'test_takers': test_takers,
                'total_responses': total_responses,
                'accuracy': accuracy
            }
        except sqlite3.OperationalError as e:
            logger.error(f"Database error for {item_bank_name}: {e}")
            return {
                'total_items': 0,
                'test_takers': 0,
                'total_responses': 0,
                'accuracy': None
            }
        finally:
            conn.close()

    # delete item bank


    def delete_item_bank(self, registry_db: Session, item_bank_name: str) -> Dict:
        """
        Delete an item bank and all associated data with proper connection handling

        Args:
            registry_db: Registry database session
            item_bank_name: Name of the item bank to delete

        Returns:
            Dict with success status and details
        """

        # Check if item bank exists
        item_bank = registry_db.query(models_registry.ItemBank).filter(
            models_registry.ItemBank.name == item_bank_name
        ).first()

        if not item_bank:
            return {
                'success': False,
                'error': f'Item bank "{item_bank_name}" not found'
            }

        # Get stats before deletion
        stats = self.get_item_bank_stats(item_bank_name)

        # Get item bank session - IMPORTANT: We need to manage this properly
        item_db = None
        try:
            item_db = item_bank_db.get_session(item_bank_name)

            # Start transaction
            item_db.begin()

            try:
                # 1. Delete all responses
                item_db.execute(text("""
                                     DELETE
                                     FROM responses
                                     WHERE session_id IN (SELECT session_id FROM assessment_sessions)
                                     """))

                # 2. Delete topic performance if table exists
                try:
                    item_db.execute(text("DELETE FROM topic_performance"))
                except:
                    pass  # Table might not exist

                # 3. Delete all assessment sessions
                item_db.query(models_itembank.AssessmentSession).delete()

                # 4. Delete all user proficiencies
                item_db.query(models_itembank.UserProficiency).delete()

                # 5. Delete all questions
                item_db.query(models_itembank.Question).delete()

                # Commit changes
                item_db.commit()

            except Exception as e:
                item_db.rollback()
                raise e

        except Exception as e:
            logger.error(f"Error deleting data from item bank {item_bank_name}: {e}")
            if item_db:
                item_db.rollback()
            # Don't return error - continue to registry cleanup
            logger.warning(f"Continuing with registry cleanup despite database error")
        finally:
            # CRITICAL: Close the item bank session
            if item_db:
                item_db.close()

            # IMPORTANT: Clean up the connection from the manager
            if hasattr(item_bank_db, 'cleanup'):
                item_bank_db.cleanup(item_bank_name)

        # Small delay to ensure connections are fully closed
        time.sleep(0.1)

        # Now delete from registry
        try:
            # Delete from user proficiency summary cache
            registry_db.query(models_registry.UserProficiencySummary).filter(
                models_registry.UserProficiencySummary.item_bank_name == item_bank_name
            ).delete()

            # Delete the item bank registry entry
            registry_db.delete(item_bank)
            registry_db.commit()

        except Exception as e:
            registry_db.rollback()
            logger.error(f"Error deleting from registry: {e}")
            return {
                'success': False,
                'error': f'Failed to delete from registry: {str(e)}'
            }

        # Now try to delete the database file and its WAL files
        db_path = item_bank_db.get_db_path(item_bank_name)
        deleted_files = []

        # Wait a moment for SQLite to release files
        time.sleep(0.2)

        # Delete all related files
        for suffix in ['', '-wal', '-shm', '-journal']:
            file_path = f"{db_path}{suffix}" if suffix else str(db_path)
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    deleted_files.append(os.path.basename(file_path))
                    logger.info(f"Deleted file: {file_path}")
                except Exception as e:
                    logger.warning(f"Could not delete {file_path}: {e}")

        logger.info(f"Successfully deleted item bank '{item_bank_name}'")

        return {
            'success': True,
            'message': f'Successfully deleted item bank "{item_bank_name}"',
            'deleted': {
                'item_bank': item_bank_name,
                'questions': stats['total_items'],
                'test_takers': stats['test_takers'],
                'responses': stats['total_responses'],
                'files': deleted_files
            }
        }