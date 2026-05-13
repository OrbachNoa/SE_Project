import argparse
import os
from src.validators.fileValidator import validate_all_files

def main():
    # Use argparse to get files from user and set them as arguments for the program
    parser = argparse.ArgumentParser(description="Upload the necessary files.")
    parser.add_argument("courses", help="Path to Courses file.")
    parser.add_argument("periods", help="Path to Exam Periods file.")
    parser.add_argument("programs", help="Path to Selected Programs file.")
    
    # Parse arguments into matching variables
    args = parser.parse_args()
    
    # Validate all files
    validate_all_files(vars(args).values())

    # Set default output path to the current user's Downloads folder
    default_path = os.path.join(os.path.expanduser("~"), "Downloads", "exam_schedules.txt")

    # Fetch output path from Environment Variable, or fallback to the default path
    output_path = os.environ.get('EXAM_OUTPUT_PATH', default_path)

    print(f"File validation successful. Output will be saved to: {output_path}")
    
    
if __name__ == "__main__":
    main()