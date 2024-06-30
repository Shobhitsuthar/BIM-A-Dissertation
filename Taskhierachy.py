import ifcopenshell
import ifcopenshell.util.sequence
import pandas as pd
import datetime
import ifcopenshell.api

# Adjusted productivity rates (units/hour)
productivity_rates = {
    "Formwork Installation": 0.8,  # m²/hour
    "Rebar Installation": 20,      # kg/hour
    "Concrete Pouring": 0.3        # m³/hour
}

def extract_elevations(ifc_element):
    bottom_elevation = top_elevation = 0
    try:
        if ifc_element.ObjectPlacement and ifc_element.Representation:
            local_bottom_z = ifc_element.ObjectPlacement.RelativePlacement.Location.Coordinates[2]
            for representation in ifc_element.Representation.Representations:
                for item in representation.Items:
                    if item.is_a("IfcBoundingBox"):
                        z_value = item.ZDim
                        bottom_elevation = local_bottom_z
                        top_elevation = local_bottom_z + z_value
                        break
    except AttributeError:
        pass
    return {'Bottom Elevation': bottom_elevation, 'Top Elevation': top_elevation}

# Define the sequence order
sequence_order = {
    'Footing': 1,
    'Beam': 2,  # Ensure Beam is before Column
    'Column': 3,
    'Wall': 4,
    'Slab': 5
}

def map_element_to_sequence(element_type):
    type_mapping = {
        'IfcFooting': 'Footing',
        'IfcColumn': 'Column',
        'IfcWall': 'Wall',
        'IfcBeam': 'Beam',
        'IfcSlab': 'Slab'
    }
    return sequence_order.get(type_mapping.get(element_type, ''), 999)

def get_cost_items_linked_to_task(ifc_file, task):
    cost_items = []
    for rel in ifc_file.by_type("IfcRelAssignsToProcess"):
        if rel.RelatingProcess == task:
            for related_object in rel.RelatedObjects:
                if related_object.is_a("IfcCostItem"):
                    cost_items.append(related_object)
    return cost_items

def calculate_task_time(task, cost_items):
    total_hours = 0
    for cost_item in cost_items:
        for quantity in cost_item.CostQuantities:
            if quantity.is_a("IfcQuantityVolume") and task.Name == "Concrete Pouring":
                total_hours += quantity.VolumeValue / productivity_rates.get("Concrete Pouring", 0.3)
            elif quantity.is_a("IfcQuantityArea") and task.Name == "Formwork Installation":
                total_hours += quantity.AreaValue / productivity_rates.get("Formwork Installation", 0.8)
            elif quantity.is_a("IfcQuantityWeight") and task.Name == "Rebar Installation":
                total_hours += quantity.WeightValue / productivity_rates.get("Rebar Installation", 20)
    return total_hours

def create_fs_relationships(ifc_file, tasks):
    for i in range(len(tasks) - 1):
        predecessor = tasks[i]
        successor = tasks[i + 1]
        ifcopenshell.api.run("sequence.assign_sequence", ifc_file, relating_process=predecessor, related_process=successor, sequence_type='FINISH_START')
        print(f"Created FS relationship: {predecessor.Name} -> {successor.Name}")

# Load the IFC file
ifc_file_path = r'Model\Test_1_Task+cost_linked.ifc'
ifc_file = ifcopenshell.open(ifc_file_path)

# Extract all building stories and their elements
story_entities = []

for story in ifc_file.by_type('IfcBuildingStorey'):
    story_elevation = story.Elevation if hasattr(story, 'Elevation') else 0
    contained_entities = []
    for rel in ifc_file.by_type('IfcRelContainedInSpatialStructure'):
        if rel.RelatingStructure == story:
            for entity in rel.RelatedElements:
                elevation = extract_elevations(entity)
                combined_bottom_elevation = story_elevation + elevation['Bottom Elevation']
                
                # Get tasks related to the element
                assigned_tasks, referenced_tasks = ifcopenshell.util.sequence.get_tasks_for_product(entity)
                
                for task in assigned_tasks + referenced_tasks:
                    # Find cost items linked to the task
                    cost_items = get_cost_items_linked_to_task(ifc_file, task)
                    cost_item_names = [cost_item.Name for cost_item in cost_items]
                    
                    print(f"Tasks for Entity '{entity.Name}': {task.Name}")
                    print(f"  Cost Items: {', '.join(cost_item_names) if cost_item_names else 'None'}")
                    
                    contained_entities.append({
                        'StoryName': story.Name,
                        'StoryGUID': story.GlobalId,
                        'StoryElevation': story_elevation,
                        'EntityName': entity.Name,
                        'EntityGUID': entity.GlobalId,
                        'EntityType': entity.is_a(),
                        'BottomElevation': combined_bottom_elevation,
                        'TopElevation': combined_bottom_elevation + (elevation['Top Elevation'] - elevation['Bottom Elevation']),
                        'SequenceOrder': map_element_to_sequence(entity.is_a()),
                        'Task': task,
                        'TaskName': task.Name,
                        'CostItems': cost_items
                    })
    contained_entities.sort(key=lambda x: (x['BottomElevation'], x['SequenceOrder']))
    story_entities.extend(contained_entities)

# Sort stories by their elevation
story_entities.sort(key=lambda x: x['StoryElevation'])

# Assign FS relationships
all_tasks = [entity['Task'] for entity in story_entities]
create_fs_relationships(ifc_file, all_tasks)

# Initialize schedule start time
current_time = datetime.datetime.now()

# Calculate task times and create/update IfcTaskTime entities
for entity in story_entities:
    task = entity['Task']
    cost_items = entity['CostItems']
    task_time_hours = calculate_task_time(task, cost_items)
    entity['EstimatedTaskTime'] = task_time_hours
    
    # Create or update IfcTaskTime entity
    task_time_entity = ifcopenshell.api.run("sequence.add_task_time", ifc_file, task=task, is_recurring=False)
    schedule_start = current_time.isoformat()
    schedule_duration = f'PT{int(task_time_hours)}H' if task_time_hours > 0 else 'PT1H'
    
    ifcopenshell.api.run("sequence.edit_task_time", ifc_file, task_time=task_time_entity, attributes={
        "ScheduleStart": schedule_start,
        "ScheduleDuration": schedule_duration
    })
    
    # Calculate finish time
    schedule_finish = (current_time + datetime.timedelta(hours=task_time_hours)).isoformat()
    
    entity['ScheduleStart'] = schedule_start
    entity['ScheduleFinish'] = schedule_finish
    entity['ScheduleDuration'] = schedule_duration
    
    # Update current_time to the finish time of the current task
    current_time += datetime.timedelta(hours=task_time_hours)
    
    print(f"  Estimated Task Time: {task_time_hours:.2f} hours")

# Create a DataFrame to store the data
simplified_df = pd.DataFrame([
    {
        'Element_GlobalId': entity['EntityGUID'],
        'Element_Name': entity['EntityName'],
        'Element_Type': entity['EntityType'],
        'Building_Story_GlobalId': entity['StoryGUID'],
        'Building_Story_Name': entity['StoryName'],
        'Task_Id': entity['Task'].GlobalId,
        'Task_Name': entity['TaskName'],
        'ScheduledStart': entity['ScheduleStart'],
        'ScheduledFinish': entity['ScheduleFinish'],
        'ScheduleDuration': entity['ScheduleDuration'],
        'ActualStart': entity['Task'].ActualStart if hasattr(entity['Task'], 'ActualStart') else None,
        'ActualFinish': entity['Task'].ActualFinish if hasattr(entity['Task'], 'ActualFinish') else None
    }
    for entity in story_entities
])

# Display the DataFrame
print(simplified_df)

# Export the DataFrame to a CSV file
csv_file_path = r'C:\Users\shobh\OneDrive - Universidade do Minho\Fraunhofer\4D Using IFC SCHEMA\Model\planned.csv'
simplified_df.to_csv(csv_file_path, index=False)

print(f"DataFrame exported to {csv_file_path}")

# Save the modified IFC file
ifc_file.write(r'Model\Test_1_Task+cost_linked_with_tasktime.ifc')

print(f"IFC file saved to 'Test_1_Task+cost_linked_with_tasktime.ifc'")
