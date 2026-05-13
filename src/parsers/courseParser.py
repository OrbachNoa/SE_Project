from .fileParser import FileParser
from ..models.enums import EvalType, Semester, Requirement, Moed
from ..models.course import Course, ProgramEntry

"""
This is the course parser.
"""
class CoursesFileParser(FileParser):

    """
    Parse the course file and return a list of course objects.
    """
    def parse(self, file_path):
        # Open the file
        with open(file_path, "r", encoding="utf-8") as file:
            content = file.read()
        
        # Validate separator, but tolerate missing if it's a single record
        try:
            FileParser.validateSeparator(content)
        except ValueError:
            pass
            
        # List to store course objects
        courses = []
        records = content.split("$$$$")
        # Iterate over all records
        for record in records:
            # If the record is not empty
            if record.strip():
                course = self._parse_course(record)
                # Check if the course is not None
                if course is not None:
                    # Validate the course
                    self._validate_course(course)
                    # Add the course to the list
                    courses.append(course)
        # Return the list of courses
        return courses

    def _validate_course(self, course):
        """
        Validate the course.
        """
        # check if the evaluation is valid
        if course.evaluation not in EvalType:
            raise ValueError(f"Invalid evaluation: {course.evaluation}")
        
        # check if the course id is valid
        if len(course.courseId) !=5 :
            raise ValueError(f"Invalid course ID: {course.courseId}")
        
        # check each program entry
        for entry in course.programEntries:
            # check if the program id is 5 digits
            if len(str(entry.programId)) != 5:
                raise ValueError(f"Invalid program ID: {entry.programId}")
            # check if the semester is valid
            if entry.semester not in Semester:
                raise ValueError(f"Invalid semester: {entry.semester}")
            # check if the requirement is valid
            if entry.requirement not in Requirement:
                raise ValueError(f"Invalid requirement: {entry.requirement}")
            # check if the year is valid
            if entry.year not in [1,2,3,4]:
                raise ValueError(f"Invalid year: {entry.year}")

    def _parse_course(self, record):
        """
        Parse the course
        """
        # Split record by lines and remove empty lines
        lines = [line.strip() for line in record.strip().split('\n') if line.strip()]
        # A valid course must have at least Name, Number, Instructor, and Evaluation
        if len(lines) < 4:
            return None  
        
        # Get the course name
        name = lines[0]
        # Get the course id
        course_id = lines[1]
        # Get the instructor
        instructor = lines[2]
        # Get the evaluation
        evaluation_str = lines[-1].upper()
        try:
            evaluation = EvalType(evaluation_str)
        except ValueError:
            evaluation = evaluation_str  # let validator handle it
            
        # List to store program entries
        program_entries = []
        # Get all program entries
        for i in range(3, len(lines) - 1):
            parts = [p.strip() for p in lines[i].split(',')]
            # A valid program entry must have 4 parts
            if len(parts) == 4:
                # Get the program id
                program_id = parts[0].strip()
                # Get the year
                try:
                    year = int(parts[1])
                except ValueError:
                    year = parts[1]
                # Get the semester
                semester_str = parts[2].upper()
                try:
                    semester = Semester(semester_str)
                except ValueError:
                    semester = semester_str
                # Get the requirement
                req_str = parts[3].upper()
                try:
                    requirement = Requirement(req_str)
                except ValueError:
                    requirement = req_str
                # Create the program entry
                entry = ProgramEntry(program_id, year, semester, requirement)
                # Add the program entry to the list
                program_entries.append(entry)
            else:
                raise ValueError(f"Invalid program entry format: {lines[i]}")
                
        # Return the course
        return Course(course_id, name, instructor, evaluation, program_entries)