# collectors/writers.py
import os
import csv
import datetime

class OutputsWriter:
    def __init__(self, output_dir, encoding='utf-8-sig'):
        self.output_dir = output_dir
        self.encoding = encoding
        os.makedirs(self.output_dir, exist_ok=True)
        
    def _get_daily_filename(self, prefix, ext):
        date_str = datetime.datetime.now().strftime('%Y%m%d')
        return os.path.join(self.output_dir, f"{prefix}_{date_str}.{ext}")

    def write_csv(self, prefix, row_dict):
        filename = self._get_daily_filename(prefix, "csv")
        file_exists = os.path.exists(filename)
        
        # To maintain dynamic fields like DiskTime_C:, DiskTime_D:, we ensure all keys are written.
        # Since fields can change if a USB drive is inserted, DictWriter is safe if we dynamically update fieldnames.
        # However, typical logging opens/closes or appends.
        # Let's read existing headers if file exists, else use row_dict.keys().
        
        fieldnames = list(row_dict.keys())
        
        if file_exists:
            with open(filename, 'r', encoding=self.encoding) as f:
                reader = csv.DictReader(f)
                try:
                    existing_fields = list(reader.fieldnames or [])
                    # Extend fieldnames with any new keys while keeping existing order
                    has_new_field = False
                    for key in fieldnames:
                        if key not in existing_fields:
                            existing_fields.append(key)
                            has_new_field = True
                    fieldnames = existing_fields
                    if has_new_field:
                        existing_rows = list(reader)
                        with open(filename, 'w', encoding=self.encoding, newline='') as rewrite_file:
                            rewrite_writer = csv.DictWriter(rewrite_file, fieldnames=fieldnames)
                            rewrite_writer.writeheader()
                            for existing_row in existing_rows:
                                rewrite_writer.writerow(existing_row)
                except StopIteration:
                    pass
        
        # Now append the row
        mode = 'a' if file_exists else 'w'
        with open(filename, mode, encoding=self.encoding, newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            if not file_exists:
                writer.writeheader()
            # If a field isn't in row_dict, dictwriter puts '' which is fine.
            writer.writerow(row_dict)

    def write_summary(self, summary_line):
        filename = self._get_daily_filename("summary", "log")
        with open(filename, 'a', encoding=self.encoding) as f:
            f.write(summary_line + "\n")
