import pandas as pd
import io

class DataManager:
    """Handles in-memory data management for behavior tracking."""

    def __init__(self):
        self.behavior_data = None # Will be a DataFrame once loaded

    def load_data_from_file(self, uploaded_file):
        """Loads data from an uploaded CSV or Excel file into memory."""
        try:
            # Set the uploaded file's internal pointer to the beginning
            uploaded_file.seek(0)
            if uploaded_file.name.endswith('.csv'):
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_excel(uploaded_file)

            # Case 1: It's a fresh roster with just one column of names
            if 'date' not in df.columns and 'color' not in df.columns:
                student_names = df.iloc[:, 0].dropna().astype(str).tolist()
                self.behavior_data = pd.DataFrame({
                    'student': student_names,
                    'date': [pd.NaT] * len(student_names), # Use NaT for dates
                    'color': [None] * len(student_names)
                }).dropna(subset=['student'])
            # Case 2: It's an existing data file
            elif 'student' in df.columns and 'date' in df.columns and 'color' in df.columns:
                self.behavior_data = df.dropna(subset=['student']).copy()
            else:
                return False, "File is not in a recognized format. It must have a single column of names, or columns named 'student', 'date', and 'color'."

            return True, f"Successfully loaded data for {len(self.get_student_list())} students."

        except Exception as e:
            return False, f"Error reading file: {str(e)}"

    def get_student_list(self):
        """Returns a list of unique student names from the loaded data."""
        if self.behavior_data is not None:
            return self.behavior_data['student'].dropna().unique().tolist()
        return []

    def add_behavior_entry(self, student_name, color, date_str):
        """Adds or updates a behavior entry in the in-memory DataFrame."""
        if self.behavior_data is None:
            return False

        # Find if an entry for this student and date already exists
        existing_entry_mask = (self.behavior_data['student'] == student_name) & (self.behavior_data['date'] == date_str)
        
        if existing_entry_mask.any():
            # Update existing entry
            self.behavior_data.loc[existing_entry_mask, 'color'] = color
        else:
            # Add new entry
            # Check if there's a placeholder row for the student with no date/color
            placeholder_mask = (self.behavior_data['student'] == student_name) & (self.behavior_data['date'].isnull())
            if placeholder_mask.any():
                # Use the first available placeholder row for this student
                idx = self.behavior_data[placeholder_mask].index[0]
                self.behavior_data.loc[idx, ['date', 'color']] = [date_str, color]
            else:
                # Append a completely new row
                new_entry = pd.DataFrame({
                    'student': [student_name],
                    'date': [date_str],
                    'color': [color]
                })
                self.behavior_data = pd.concat([self.behavior_data, new_entry], ignore_index=True)
        return True

    def get_student_behavior_data(self, student_name):
        """Gets all valid behavior data for a specific student."""
        if self.behavior_data is None:
            return pd.DataFrame()
        
        student_data = self.behavior_data[
            (self.behavior_data['student'] == student_name) &
            (self.behavior_data['date'].notna())
        ].copy()
        
        if not student_data.empty:
            student_data['date'] = pd.to_datetime(student_data['date'])
        
        return student_data

    def get_all_behavior_data(self):
        """Returns the entire in-memory DataFrame, excluding placeholder rows."""
        if self.behavior_data is not None:
            return self.behavior_data[self.behavior_data['date'].notna()].copy()
        return pd.DataFrame()

    def get_data_for_download(self):
        """Prepares the data for download by cleaning it and returning as CSV bytes."""
        if self.behavior_data is None:
            return None
        # Return a clean version without placeholder rows
        clean_df = self.behavior_data[self.behavior_data['date'].notna()].copy()
        return clean_df.to_csv(index=False).encode('utf-8')

    def clear_student_data(self, student_name):
        """Clears behavior data for a specific student in the current session."""
        if self.behavior_data is not None:
            # We just nullify their date/color entries, keeping the student record
            self.behavior_data.loc[self.behavior_data['student'] == student_name, ['date', 'color']] = [pd.NaT, None]
            return True
        return False

    def clear_all_data(self):
        """Clears all behavior data in the current session."""
        if self.behavior_data is not None:
            # Nullify all date/color entries, keeping the student names
            self.behavior_data[['date', 'color']] = [pd.NaT, None]
            return True
        return False
