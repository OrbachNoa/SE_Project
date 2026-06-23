import csv

class BaseCsvWriter:
    """
    Generic infrastructure component for writing tabular data to an Excel-compatible CSV file.
    It expects a list of headers and a matrix (list of lists) of strings for the rows.
    """
    
    @staticmethod
    def write(path: str, headers: list[str], rows: list[list[str]]) -> None:
        if not path:
            return
            
        # Using utf-8-sig encoding ensures that Excel opens the file correctly (handles Hebrew/Special chars)
        with open(path, mode='w', newline='', encoding='utf-8-sig') as file:
            writer = csv.writer(file)
            
            # Write the header row
            writer.writerow(headers) 
            
            # Write all data rows at once
            writer.writerows(rows)