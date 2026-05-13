import argparse
from src.fileValidator import validate_all_files

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
    
    
if __name__ == "__main__":
    main()