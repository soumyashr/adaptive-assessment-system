#!/usr/bin/env python3
"""
Batch CSV Cleaner Script
Processes CSV files from raw_sample_questions folder, cleans them,
and saves to sample_questions folder.

Directory structure:
backend/
├── scripts/
│   └── clean_csv_files.py (this script)
└── data/
    ├── logs/
    │   └── cleaning_log_*.log
    ├── raw_sample_questions/
    │   ├── *.csv (files to process)
    │   └── processed/
    │       ├── *_processed_*.csv
    │       └── *_failed_*.csv
    └── sample_questions/
        └── *_cleaned.csv

Usage: python backend/scripts/clean_csv_files.py
"""

import os
import csv
import re
import shutil
from datetime import datetime
from pathlib import Path
import logging

# Setup paths
SCRIPT_DIR = Path(__file__).resolve().parent  # backend/scripts
BACKEND_DIR = SCRIPT_DIR.parent  # backend folder
DATA_DIR = BACKEND_DIR / "data"  # backend/data
RAW_DIR = DATA_DIR / "raw_sample_questions"
CLEANED_DIR = DATA_DIR / "sample_questions"
PROCESSED_DIR = RAW_DIR / "processed"  # Subdirectory for processed files
LOG_DIR = DATA_DIR / "logs"

# Create log directory if it doesn't exist
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Setup logging
LOG_FILE = LOG_DIR / f"cleaning_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class CSVCleaner:
    """Cleans CSV files following the established pattern"""

    def __init__(self):
        self.stats = {
            'total_files': 0,
            'success': 0,
            'failed': 0,
            'total_questions': 0,
            'files_processed': []
        }

    def clean_csv_file(self, filepath):
        """
        Clean a single CSV file

        Args:
            filepath: Path to the CSV file

        Returns:
            dict: Cleaned content and statistics
        """
        logger.info(f"Processing: {filepath.name}")

        try:
            # Read the file with multiple encoding attempts
            content = None
            encodings = ['utf-8-sig', 'utf-8', 'cp1252', 'iso-8859-1']

            for encoding in encodings:
                try:
                    with open(filepath, 'r', encoding=encoding) as f:
                        content = f.read()
                    logger.debug(f"Successfully read file with {encoding} encoding")
                    break
                except UnicodeDecodeError:
                    continue

            if content is None:
                raise ValueError("Could not read file with any supported encoding")

            # Remove BOM if present
            content = content.replace('\ufeff', '')

            # Split into lines and remove empty
            lines = [line.strip() for line in content.split('\n') if line.strip()]

            if not lines:
                raise ValueError("File is empty or contains only empty lines")

            # Remove extra quotes wrapping entire lines
            lines = [self._remove_wrapper_quotes(line) for line in lines]

            # Parse CSV
            rows = []
            header = None

            for i, line in enumerate(lines):
                values = self._parse_csv_line(line)
                if i == 0:
                    header = [h.strip().lower() for h in values]
                    if not self._validate_headers(header):
                        raise ValueError(f"Missing required columns. Found: {header}")
                else:
                    if len(values) >= len(header):
                        rows.append(values)

            if not rows:
                raise ValueError("No data rows found in file")

            # Clean and format the data
            cleaned_data = self._format_csv_data(rows, header, filepath.stem)

            logger.info(f"✓ Cleaned {filepath.name}: {cleaned_data['stats']['total']} questions")
            return cleaned_data

        except Exception as e:
            logger.error(f"✗ Failed to clean {filepath.name}: {str(e)}")
            raise

    def _remove_wrapper_quotes(self, line):
        """Remove quotes wrapping entire line"""
        if line.startswith('"') and line.endswith('"'):
            return line[1:-1]
        return line

    def _parse_csv_line(self, line):
        """Parse a CSV line handling quotes and commas"""
        values = []
        current = ''
        in_quotes = False
        i = 0

        while i < len(line):
            char = line[i]

            if char == '"':
                if in_quotes and i + 1 < len(line) and line[i + 1] == '"':
                    current += '"'
                    i += 2
                    continue
                else:
                    in_quotes = not in_quotes
            elif char == ',' and not in_quotes:
                values.append(current.strip())
                current = ''
            else:
                current += char

            i += 1

        values.append(current.strip())
        return values

    def _validate_headers(self, headers):
        """Check if all required headers are present"""
        required = ['question', 'option_a', 'option_b', 'option_c', 'option_d',
                    'answer', 'tier', 'topic']
        missing = [h for h in required if h not in headers]
        if missing:
            logger.warning(f"Missing headers: {missing}")
        return all(h in headers for h in required)

    def _format_csv_data(self, rows, header, filename_stem):
        """Format the CSV data with new structure"""
        new_headers = ['subject', 'question_id', 'question', 'option_a', 'option_b',
                       'option_c', 'option_d', 'answer', 'topic', 'tier',
                       'discrimination_a', 'difficulty_b', 'guessing_c']

        cleaned_rows = []
        tier_counts = {'C1': 0, 'C2': 0, 'C3': 0, 'C4': 0}

        # Generate ID prefix from filename
        id_prefix = re.sub(r'[^a-z0-9]', '', filename_stem.lower())

        for idx, row in enumerate(rows, 1):
            try:
                # Extract values safely
                question = self._safe_get(row, header, 'question')
                option_a = self._safe_get(row, header, 'option_a')
                option_b = self._safe_get(row, header, 'option_b')
                option_c = self._safe_get(row, header, 'option_c')
                option_d = self._safe_get(row, header, 'option_d')

                # Fix answer format (option_a -> a)
                answer = self._safe_get(row, header, 'answer').lower().strip()
                if answer.startswith('option_'):
                    answer = answer.replace('option_', '')

                # Validate answer
                if answer not in ['a', 'b', 'c', 'd']:
                    logger.warning(f"Invalid answer '{answer}' in row {idx}, defaulting to 'a'")
                    answer = 'a'

                # Standardize tier
                tier = self._safe_get(row, header, 'tier').upper().strip()
                if not tier.startswith('C'):
                    tier = 'C' + tier

                # Validate tier
                if tier not in ['C1', 'C2', 'C3', 'C4']:
                    logger.warning(f"Invalid tier '{tier}' in row {idx}, defaulting to 'C2'")
                    tier = 'C2'

                # Get topic
                topic_raw = self._safe_get(row, header, 'topic')

                # Format topic name
                if topic_raw and '-' not in topic_raw:
                    base_topic = ' '.join(word.capitalize() for word in filename_stem.replace('_', ' ').split())
                    topic = f"{base_topic} - {topic_raw}"
                else:
                    topic = topic_raw

                # Escape CSV values
                question = self._escape_csv(question)
                option_a = self._escape_csv(option_a)
                option_b = self._escape_csv(option_b)
                option_c = self._escape_csv(option_c)
                option_d = self._escape_csv(option_d)
                topic = self._escape_csv(topic)

                # Count tiers
                tier_counts[tier] += 1

                # Set IRT parameters based on tier
                difficulty_map = {
                    'C1': '-1.0',
                    'C2': '-0.5',
                    'C3': '0.5',
                    'C4': '1.0'
                }
                difficulty_b = difficulty_map.get(tier, '0.0')

                # Build cleaned row
                cleaned_row = [
                    'maths',  # subject
                    f"{id_prefix}_{idx:03d}",  # question_id
                    question,
                    option_a,
                    option_b,
                    option_c,
                    option_d,
                    answer,
                    topic,
                    tier,
                    '1.5',  # discrimination_a
                    difficulty_b,
                    '0.25'  # guessing_c
                ]

                cleaned_rows.append(cleaned_row)

            except Exception as e:
                logger.warning(f"Skipping row {idx}: {str(e)}")

        return {
            'headers': new_headers,
            'rows': cleaned_rows,
            'stats': {
                'total': len(cleaned_rows),
                'tiers': tier_counts
            }
        }

    def _safe_get(self, row, header, column_name):
        """Safely get value from row"""
        try:
            index = header.index(column_name)
            if index < len(row):
                return row[index]
        except (ValueError, IndexError):
            pass
        return ''

    def _escape_csv(self, value):
        """Escape CSV value if needed"""
        if not value:
            return '""'

        value = str(value)

        # If contains comma, newline, or quote, wrap in quotes
        if ',' in value or '\n' in value or '"' in value:
            # Escape internal quotes
            value = value.replace('"', '""')
            return f'"{value}"'

        return value

    def process_all_files(self):
        """Process all CSV files in the raw directory"""
        # Create directories if they don't exist
        RAW_DIR.mkdir(parents=True, exist_ok=True)
        CLEANED_DIR.mkdir(parents=True, exist_ok=True)
        PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

        logger.info("=" * 60)
        logger.info("CSV BATCH CLEANING STARTED")
        logger.info("=" * 60)
        logger.info(f"Script location: {SCRIPT_DIR}")
        logger.info(f"Raw directory: {RAW_DIR}")
        logger.info(f"Cleaned directory: {CLEANED_DIR}")
        logger.info(f"Log directory: {LOG_DIR}")
        logger.info("-" * 60)

        # Find all CSV files in raw directory (excluding subdirectories)
        csv_files = [f for f in RAW_DIR.glob("*.csv") if f.is_file()]

        if not csv_files:
            logger.warning("No CSV files found in raw_sample_questions directory")
            logger.info("Place CSV files in: " + str(RAW_DIR))
            return

        logger.info(f"Found {len(csv_files)} CSV files to process")
        logger.info("-" * 60)

        for csv_file in csv_files:
            self.stats['total_files'] += 1

            try:
                # Clean the file
                result = self.clean_csv_file(csv_file)

                # Save cleaned file
                cleaned_filename = csv_file.stem + "_cleaned.csv"
                cleaned_path = CLEANED_DIR / cleaned_filename

                with open(cleaned_path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(result['headers'])
                    writer.writerows(result['rows'])

                # Move original to processed folder with timestamp
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                processed_filename = f"{csv_file.stem}_processed_{timestamp}.csv"
                processed_path = PROCESSED_DIR / processed_filename
                shutil.move(str(csv_file), str(processed_path))

                self.stats['success'] += 1
                self.stats['total_questions'] += result['stats']['total']
                self.stats['files_processed'].append(cleaned_filename)

                logger.info(f"✓ Saved cleaned: {cleaned_filename}")
                logger.info(f"  Original moved to: processed/{processed_filename}")

                # Log tier distribution
                tier_info = ', '.join([f"{k}:{v}" for k, v in result['stats']['tiers'].items() if v > 0])
                logger.info(f"  Questions: {result['stats']['total']} | Tiers: {tier_info}")
                logger.info("-" * 60)

            except Exception as e:
                self.stats['failed'] += 1
                logger.error(f"✗ Failed to process {csv_file.name}: {str(e)}")

                # Move failed file to processed folder with failed marker
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                failed_filename = f"{csv_file.stem}_failed_{timestamp}.csv"
                failed_path = PROCESSED_DIR / failed_filename

                try:
                    shutil.move(str(csv_file), str(failed_path))
                    logger.info(f"  Failed file moved to: processed/{failed_filename}")
                except Exception as move_error:
                    logger.error(f"  Could not move failed file: {move_error}")

                logger.info("-" * 60)

        # Print summary
        self._print_summary()

    def _print_summary(self):
        """Print processing summary"""
        logger.info("=" * 60)
        logger.info("PROCESSING COMPLETE - SUMMARY")
        logger.info("=" * 60)
        logger.info(f"📊 Total files processed: {self.stats['total_files']}")
        logger.info(f"✅ Successful: {self.stats['success']}")
        logger.info(f"❌ Failed: {self.stats['failed']}")
        logger.info(f"📝 Total questions cleaned: {self.stats['total_questions']}")

        if self.stats['files_processed']:
            logger.info(f"\n📁 Cleaned files saved to: {CLEANED_DIR}")
            for filename in self.stats['files_processed']:
                logger.info(f"   - {filename}")

        logger.info(f"\n📋 Log file: {LOG_FILE.name}")
        logger.info(f"📂 Full log path: {LOG_FILE}")
        logger.info("=" * 60)

        # Also print to console for convenience
        print(f"\n✅ Processing complete!")
        print(f"   - Cleaned {self.stats['success']} files ({self.stats['total_questions']} questions)")
        print(f"   - Check {CLEANED_DIR} for cleaned files")
        print(f"   - Check {LOG_FILE.name} for detailed log")


def main():
    """Main function"""
    try:
        # Print startup info
        print("🚀 Starting CSV Batch Cleaner...")
        print(f"   Looking for files in: backend/data/raw_sample_questions/")

        cleaner = CSVCleaner()
        cleaner.process_all_files()

    except KeyboardInterrupt:
        logger.info("\n⚠ Process interrupted by user")
        print("\n⚠ Process interrupted")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        print(f"\n❌ Error: {str(e)}")
        print(f"   Check log file for details: backend/data/logs/")
        raise


if __name__ == "__main__":
    main()