import pandas as pd
import ifcopenshell
import ifcopenshell.api

def read_csv_tasks(file_path):
    # Read the CSV file
    df = pd.read_csv(file_path)
    
    # Debug: Print the DataFrame to inspect its content
    print("DataFrame loaded from CSV:")
    print(df)
    
    # Strip any whitespace from column values
    df['IfcEntity'] = df['IfcEntity'].str.strip()
    
    # Identify parent and child tasks
    df['Is Parent Task'] = df['Parent'].apply(lambda x: str(x).count('.') < 2)
    
    # Process the tasks into a dictionary
    tasks = {}
    for _, row in df.iterrows():
        ifc_entity = row['IfcEntity']
        task_id = row['Parent']
        task_name = row['Task Name']
        is_parent_task = row['Is Parent Task']
        
        # Skip parent tasks
        if pd.isna(ifc_entity) or is_parent_task:
            continue

        if ifc_entity not in tasks:
            tasks[ifc_entity] = []

        tasks[ifc_entity].append({
            "Parent": task_id,
            "Task Name": task_name,
        })
    
    # Debug: Print the tasks dictionary to inspect its content
    print("Tasks dictionary created from CSV:")
    for key, value in tasks.items():
        print(f"{key}: {value}")

    return tasks

def append_tasks_to_ifc_elements(ifc_file, tasks, schedule):
    for ifc_entity, task_list in tasks.items():
        print(f"Processing IFC entity type: {ifc_entity}")
        elements = ifc_file.by_type(ifc_entity)
        print(f"Found {len(elements)} elements of type {ifc_entity}")
        
        # Debugging: Print element details
        for element in elements:
            print(f"Element {element.GlobalId}, {element.Name}")
        
        for element in elements:
            for task in task_list:
                task_obj = ifcopenshell.api.run("sequence.add_task", ifc_file, work_schedule=schedule, parent_task=None,
                                                name=task["Task Name"], predefined_type='NOTDEFINED')
                # Assign the task to the product (element)
                ifcopenshell.api.run("sequence.assign_product", ifc_file, relating_product=element, related_object=task_obj)
                print(f"Task '{task['Task Name']}' assigned to element '{element.GlobalId}'")

def main(csv_file_path, ifc_file_path, output_ifc_file_path):
    # Read tasks from CSV file
    tasks = read_csv_tasks(csv_file_path)
    print(f"Tasks read from CSV: {tasks}")
    
    # Open the IFC file
    ifc_file = ifcopenshell.open(ifc_file_path)
    
    # Create a work schedule
    schedule = ifcopenshell.api.run("sequence.add_work_schedule", ifc_file, name="Construction Schedule A")
    print(f"Work schedule created: {schedule}")
    
    # Append tasks to IFC elements
    append_tasks_to_ifc_elements(ifc_file, tasks, schedule)
    
    # Save the modified IFC file
    ifc_file.write(output_ifc_file_path)
    print(f"Modified IFC file saved at {output_ifc_file_path}.")

# Example usage
csv_file_path = r'WBS\WBS_Concrete_Building.csv'  # Ensure this path matches your CSV file location
ifc_file_path = r'C:\Users\shobh\OneDrive - Universidade do Minho\Fraunhofer\4D Using IFC SCHEMA\Model\Test_1.ifc'
output_ifc_file_path = r'C:\Users\shobh\OneDrive - Universidade do Minho\Fraunhofer\4D Using IFC SCHEMA\Model\Test_1_Task.ifc'

main(csv_file_path, ifc_file_path, output_ifc_file_path)
