import ifcopenshell
import ifcopenshell.util.cost
import ifcopenshell.util.sequence

# Load the IFC file
file_path = r'C:\Users\shobh\OneDrive - Universidade do Minho\Fraunhofer\4D Using IFC SCHEMA\Model\Test_1_Task+cost.ifc'
ifc_file = ifcopenshell.open(file_path)

# Function to retrieve cost items and referenced tasks for all building elements
def get_cost_items_and_referenced_tasks_for_all_building_elements(ifc_file):
    building_elements = ifc_file.by_type("IfcBuildingElement")
    for element in building_elements:
        # Get cost items
        cost_items = ifcopenshell.util.cost.get_cost_items_for_product(element)
        print(f'Building Element: {element.GlobalId}')
        print('  Cost Items:')
        for cost_item in cost_items:
            print(f'    Cost Item: {cost_item.GlobalId} - {cost_item.Name}')
            # Check if cost item has IfcQuantityVolume or IfcQuantityArea
            if cost_item.CostQuantities:  # Check if CostQuantities is not None
                for quantity in cost_item.CostQuantities:
                    if quantity.is_a('IfcQuantityVolume'):
                        volume_quantity = quantity
                        print(f'      Volume Quantity: {volume_quantity.Name} - {volume_quantity.VolumeValue} m3')
                        # Link to Concrete Pouring task
                        link_cost_item_to_specific_task(ifc_file, cost_item, "Concrete Pouring", element)
                    elif quantity.is_a('IfcQuantityArea'):
                        area_quantity = quantity
                        print(f'      Area Quantity: {area_quantity.Name} - {area_quantity.AreaValue} m2')
                        # Link to Formwork Installation task
                        link_cost_item_to_specific_task(ifc_file, cost_item, "Formwork Installation", element)
            else:
                print('      No CostQuantities available for this cost item.')
        
        # Get referenced tasks
        _, referenced_tasks = ifcopenshell.util.sequence.get_tasks_for_product(element)
        print('  Referenced Tasks:')
        for task in referenced_tasks:
            print(f'    Referenced Task: {task.GlobalId} - {task.Name}')

# Function to find a task by name and element
def find_task_by_name_and_element(task_name, referenced_tasks):
    for task in referenced_tasks:
        if task.Name == task_name:
            return task
    return None

# Function to link a cost item to a specific task based on task name and element
def link_cost_item_to_specific_task(ifc_file, cost_item, task_name, element):
    _, referenced_tasks = ifcopenshell.util.sequence.get_tasks_for_product(element)
    task = find_task_by_name_and_element(task_name, referenced_tasks)
    if task:
        print(f'      Found Task {task.GlobalId} ({task.Name}) for linking')
        if not is_cost_item_linked_to_task(cost_item, task):
            link_cost_item_to_task(ifc_file, cost_item, task)
            print(f'      Linked Cost Item {cost_item.GlobalId} to Task {task.GlobalId} ({task.Name})')
        else:
            print(f'      Cost Item {cost_item.GlobalId} is already linked to Task {task.GlobalId} ({task.Name})')
    else:
        print(f'      Task {task_name} not found for Element {element.GlobalId}')

# Helper function to check if a cost item is already linked to a task
def is_cost_item_linked_to_task(cost_item, task):
    for rel in ifc_file.by_type("IfcRelAssignsToProcess"):
        if rel.RelatingProcess == task and cost_item in rel.RelatedObjects:
            return True
    return False

# Function to link a cost item to a task using IfcRelAssignsToProcess
def link_cost_item_to_task(ifc_file, cost_item, task):
    rel_assign = ifc_file.create_entity(
        "IfcRelAssignsToProcess",
        GlobalId=ifcopenshell.guid.new(),
        OwnerHistory=None,
        Name=None,
        Description=None,
        RelatedObjects=[cost_item],
        RelatingProcess=task
    )
    ifc_file.add(rel_assign)

# Get cost items, referenced tasks, and link them for all IfcBuildingElement instances
get_cost_items_and_referenced_tasks_for_all_building_elements(ifc_file)

# Save the modified IFC file
output_file_path = r'C:\Users\shobh\OneDrive - Universidade do Minho\Fraunhofer\4D Using IFC SCHEMA\Model\Test_1_Task+cost_linked.ifc'
ifc_file.write(output_file_path)

print(f"Modified IFC file saved to {output_file_path}")
