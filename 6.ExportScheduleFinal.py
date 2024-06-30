import ifcopenshell
import pandas as pd
import ifcopenshell.util.sequence
import ifcopenshell.util.cost

# Load the existing IFC file
ifc_file = ifcopenshell.open(r'Model\Test_1_Task+cost_linked_with_tasktime.ifc')

# Function to safely extract values
def get_wrapped_value(attr):
    return attr.wrappedValue if hasattr(attr, 'wrappedValue') else attr

# Function to find cost items linked to a task
def get_cost_items_linked_to_task(ifc_file, task):
    cost_items = []
    for rel in ifc_file.by_type("IfcRelAssignsToProcess"):
        if rel.RelatingProcess == task:
            for related_object in rel.RelatedObjects:
                if related_object.is_a("IfcCostItem"):
                    cost_items.append(related_object)
    return cost_items

# Function to collect elements with referenced tasks, task times, cost items, and quantities into a list of dictionaries
def collect_element_task_data(ifc_file):
    data = []
    elements = ifc_file.by_type("IfcElement")
    
    for element in elements:
        assigned_tasks, referenced_tasks = ifcopenshell.util.sequence.get_tasks_for_product(element)
        
        for idx, task in enumerate(referenced_tasks):
            task_time = task.TaskTime
            cost_items = get_cost_items_linked_to_task(ifc_file, task)
            
            if not cost_items:
                element_data = {
                    'Element': f"{element.GlobalId}",
                    'Task': f"{task.Name}",
                    'TaskID': f"{task.GlobalId}",
                    'QuantityType': None,
                    'QuantityValue': 0,
                    'TotalCost': 0
                }
                data.append(element_data)
            else:
                for cost_item in cost_items:
                    total_cost = 0
                    for quantity in cost_item.CostQuantities:
                        if quantity.is_a('IfcQuantityVolume'):
                            quantity_type = 'Volume'
                            quantity_value = quantity.VolumeValue
                        elif quantity.is_a('IfcQuantityArea'):
                            quantity_type = 'Area'
                            quantity_value = quantity.AreaValue
                        else:
                            quantity_type = 'Other'
                            quantity_value = None

                        if quantity_value is not None:
                            for related_cost_value in cost_item.CostValues:
                                if related_cost_value.is_a('IfcCostValue'):
                                    cost_value = related_cost_value.AppliedValue.wrappedValue
                                    total_cost += quantity_value * cost_value

                        element_data = {
                            'Element': f"{element.GlobalId}",
                            'Task': f"{task.Name}",
                            'TaskID': f"{task.GlobalId}",
                            'QuantityType': quantity_type,
                            'QuantityValue': quantity_value,
                            'TotalCost': total_cost
                        }
                        data.append(element_data)
    
    return data

# Collect data into a list of dictionaries
element_task_data = collect_element_task_data(ifc_file)

# Convert to DataFrame
df = pd.DataFrame(element_task_data)

# Print the DataFrame (optional, for verification)
print(df)

# Save DataFrame to CSV (optional)
df.to_csv('costdata.csv', index=False)

# Output message when done
print("Finished processing tasks and their linked cost items.")
