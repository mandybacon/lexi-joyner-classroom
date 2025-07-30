class BehaviorTracker:
    """Handles behavior color system and related functionality"""
    
    def __init__(self):
        # Define behavior colors from worst to best
        self.colors = {
            'Red': '#FF0000',      # Bad
            'Orange': '#FF8C00',   # Less bad
            'Yellow': '#FFD700',   # Needs improvement
            'Green': '#32CD32',    # Good
            'Blue': '#4169E1',     # Very good
            'Purple': '#8A2BE2',   # Great
            'Pink': '#FF69B4'      # Excellent
        }
        
        self.color_descriptions = {
            'Red': 'Poor behavior - needs immediate attention',
            'Orange': 'Below expectations - requires improvement',
            'Yellow': 'Needs improvement - making progress',
            'Green': 'Good behavior - meeting expectations',
            'Blue': 'Very good behavior - exceeding expectations',
            'Purple': 'Great behavior - consistently excellent',
            'Pink': 'Excellent behavior - exemplary student'
        }
        
        # Point system for behavior tracking
        self.color_points = {
            'Red': -3,      # 3 bad points
            'Orange': -2,   # 2 bad points
            'Yellow': -1,   # 1 bad point
            'Green': 1,     # 1 good point
            'Blue': 2,      # 2 good points
            'Purple': 3,    # 3 good points
            'Pink': 4       # 4 good points
        }
    
    def get_color_options(self):
        """Return the color mapping dictionary"""
        return self.colors
    
    def get_color_descriptions(self):
        """Return color descriptions"""
        return self.color_descriptions
    
    def get_color_value(self, color_name):
        """Get the numeric value of a color (0-6, higher is better)"""
        color_names = list(self.colors.keys())
        try:
            return color_names.index(color_name)
        except ValueError:
            return 0  # Default to worst if color not found
    
    def get_color_hex(self, color_name):
        """Get the hex color code for a given color name"""
        return self.colors.get(color_name, '#000000')
    
    def validate_color(self, color_name):
        """Check if a color name is valid"""
        return color_name in self.colors
    
    def get_color_points(self, color_name):
        """Get the point value for a given color"""
        return self.color_points.get(color_name, 0)
    
    def calculate_points_summary(self, student_data):
        """Calculate good points, bad points, and percentage for a student"""
        if student_data.empty:
            return {
                'total_good_points': 0,
                'total_bad_points': 0,
                'total_points': 0,
                'good_percentage': 0,
                'days_recorded': 0
            }
        
        total_good_points = 0
        total_bad_points = 0
        
        for _, row in student_data.iterrows():
            points = self.get_color_points(row['color'])
            if points > 0:
                total_good_points += points
            else:
                total_bad_points += abs(points)
        
        total_points = total_good_points + total_bad_points
        good_percentage = (total_good_points / total_points * 100) if total_points > 0 else 0
        days_recorded = len(student_data)
        
        return {
            'total_good_points': total_good_points,
            'total_bad_points': total_bad_points,
            'total_points': total_points,
            'good_percentage': round(good_percentage, 1),
            'days_recorded': days_recorded
        }
    
