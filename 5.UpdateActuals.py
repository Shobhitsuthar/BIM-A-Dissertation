import ifcopenshell
import pandas as pd
from datetime import datetime
import ifcopenshell.util.sequence

def update_ifc_with_actuals_and_compute_completion(ifc_file_path, csv_file_path):
    # Load the existing IFC file
    ifc_file = ifcopenshell.open(ifc_file_path)
    
    try:
        # Read updated CSV file with specified encoding
        updated_df = pd.read_csv(csv_file_path, encoding='latin-1')  # or encoding='cp1252' if latin-1 doesn't work
    except pd.errors.ParserError as e:
        print(f"ParserError: {e}")
        return

    # Print column names to ensure correct identification
    print("Columns in CSV:", updated_df.columns.tolist())
    
    completion_data = []
    
    # Update IFC file with actual start and finish dates and compute completion
    for index, row in updated_df.iterrows():
        # Check if 'Element_GlobalId' and 'Task_Id' columns are NaN or missing
        if pd.isna(row['Element_GlobalId']) or pd.isna(row['Task_Id']):
            print(f"Skipping row {index} due to NaN values.")
            continue
        
        # Extract element GUID
        element_guid = str(row['Element_GlobalId']).split(' - ')[0]  # Convert to string before splitting
        
        # Extract task GUID
        task_guid = str(row['Task_Id']).split(' - ')[0]  # Convert to string before splitting
        
        # Find corresponding IfcElement and IfcTask in the IFC file
        element = ifc_file.by_guid(element_guid)
        task = ifc_file.by_guid(task_guid)
        
        # Check if element and task are found
        if element is None:
            print(f"Element with GUID {element_guid} not found.")
            continue
        if task is None:
            print(f"Task with GUID {task_guid} not found.")
            continue
        
        # Parse dates
        def parse_date(date_str):
            try:
                return datetime.fromisoformat(date_str)
            except ValueError:
                return pd.to_datetime(date_str, format='%d-%m-%Y %H:%M')
        
        # Update actual start and finish dates in the IFC file
        if 'ActualStart' in row and pd.notna(row['ActualStart']):
            actual_start = parse_date(row['ActualStart'])
            task.TaskTime.ActualStart = actual_start.isoformat()
        if 'ActualFinish' in row and pd.notna(row['ActualFinish']):
            actual_finish = parse_date(row['ActualFinish'])
            task.TaskTime.ActualFinish = actual_finish.isoformat()
        
        # Initialize Schedule_duration to avoid UnboundLocalError
        Schedule_duration = 0
        
        # Calculate and update actual duration if both actual start and finish are present
        if 'ActualStart' in row and pd.notna(row['ActualStart']):
            actual_start = parse_date(row['ActualStart'])
            
            if 'ActualFinish' in row and pd.notna(row['ActualFinish']):
                actual_finish = parse_date(row['ActualFinish'])
                actual_duration = (actual_finish - actual_start).days
                
                # Update actual duration in the IFC file
                task.TaskTime.ActualDuration = f"P{actual_duration}D"
                
                # Set completion percentage to 100% as the task is completed
                completion_percentage = 100
            else:
                current_date = datetime.now()
                actual_duration = (current_date - actual_start).days
                
                # Calculate Schedule duration
                if 'ScheduleStart' in row and pd.notna(row['ScheduleStart']) and 'ScheduleFinish' in row and pd.notna(row['ScheduleFinish']):
                    Schedule_start = parse_date(row['ScheduleStart'])
                    Schedule_finish = parse_date(row['ScheduleFinish'])
                    Schedule_duration = (Schedule_finish - Schedule_start).days
                
                # Calculate completion percentage
                if Schedule_duration > 0:
                    completion_percentage = (actual_duration / Schedule_duration) * 100
                else:
                    completion_percentage = 0
            
            # Update completion in the IFC file
            task.TaskTime.Completion = completion_percentage
            
            completion_data.append({
                'Element_GlobalId': row['Element_GlobalId'],
                'Task_Id': row['Task_Id'],
                'ScheduleDuration': Schedule_duration,
                'ActualDuration': actual_duration,
                'CompletionPercentage': completion_percentage
            })
    
    # Save updated IFC file
    updated_ifc_file_path = 'updated_ifc_file.ifc'
    ifc_file.write(updated_ifc_file_path)
    print(f"Updated IFC file saved: {updated_ifc_file_path}")
    
    # Save completion data to a new CSV file
    completion_df = pd.DataFrame(completion_data)
    completion_df.to_csv('completion_data.csv', index=False)
    print(f"Completion data saved to: completion_data.csv")

# Example usage:
if __name__ == "__main__":
    # Replace these paths with your actual paths
    ifc_file_path = r'Model\Test_1_Task+cost_linked_with_tasktime.ifc'
    updated_csv_path = r'Model\Actual.csv'
    
    update_ifc_with_actuals_and_compute_completion(ifc_file_path, updated_csv_path)
