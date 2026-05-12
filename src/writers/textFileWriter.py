class TextFileWriter:
    """
    A simple text file writer for outputting the generated schedule.
    """
    def write(self, schedule, filename):
        with open(filename, 'w') as f:
            for assignment in schedule.get_assignments():
                line = f"{assignment.course.code} - {assignment.date} - {assignment.semester} - {assignment.moed}\n"
                f.write(line)