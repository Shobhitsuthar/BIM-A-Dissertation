import ifcopenshell
import pandas as pd
import ifcopenshell.util.element
import ifcopenshell.api

def open_ifc_file(ifc_file_path):
    """
    Open an IFC file and extract data about building elements.

    Args:
    - ifc_file_path (str): File path to the IFC file.

    Returns:
    - list: List of dictionaries containing extracted data for each building element.
    """
    extracted_data = []
    try:
        ifc_file = ifcopenshell.open(ifc_file_path)
        elements = ifc_file.by_type("IfcBuildingElement")
        
        for element in elements:
            entity_type = element.is_a().replace("Ifc", "")
            qto_set_name = f"Qto_{entity_type}BaseQuantities"
            
            qto_sets = ifcopenshell.util.element.get_psets(element)
            qto_set = qto_sets.get(qto_set_name, {})
            
            volume = qto_set.get("NetVolume") if qto_set else None
            area = qto_set.get("OuterSurfaceArea") if qto_set else None
            
            bol_codes = {}
            qto_pset = ifcopenshell.util.element.get_pset(element, "Cost_Codes")
            if qto_pset:
                for prop_name, prop_value in qto_pset.items():
                    if prop_name.startswith("BOL.Code"):
                        bol_codes[prop_name] = prop_value
            
            extracted_data.append({
                "IfcGuid": element.GlobalId,
                "Volume": volume,
                "SurfaceArea": area,
                "BolCodes": bol_codes
            })
            
            print(f"Volume for element #{element.id()}: {volume}")
            print(f"BOL Codes for element #{element.id()}: {bol_codes}")
            print(f"Area for element #{element.id()}: {area}")
        
    except Exception as e:
        print(f"Error: {e}")
    
    return extracted_data

def search_bol_code(csv_file_path, extracted_data):
    """
    Search for BOL codes in a CSV file and match them with extracted data.

    Args:
    - csv_file_path (str): File path to the CSV file containing BOL codes.
    - extracted_data (list): List of dictionaries containing extracted data for each building element.

    Modifies:
    - Updates each dictionary in extracted_data with matches found in the CSV file.
    """
    try:
        df = pd.read_csv(csv_file_path, encoding="ISO-8859-1")
        
        if "Code" in df.columns:
            for data in extracted_data:
                bol_codes = data["BolCodes"]
                data["Matches"] = []
                for code_name, bol_code in bol_codes.items():
                    if bol_code and bol_code.strip() in df["Code"].str.strip().values:
                        print(f"Bol.Code value '{bol_code}' found in the CSV file.")
                        row_index = df.index[df["Code"].str.strip() == bol_code.strip()].tolist()[0]
                        match_info = {
                            "Description": df.at[row_index, 'Description'],
                            "UnitOfMeasurement": df.at[row_index, 'Unit of measurement'],
                            "Price": df.at[row_index, 'Price / Prezzo'],
                            "BolCode": bol_code
                        }
                        data["Matches"].append(match_info)
                    else:
                        print(f"Bol.Code value '{bol_code}' not found in the CSV file.")
        else:
            print("Column 'Code' not found in the CSV file.")

    except Exception as e:
        print(f"Error: {e}")

def create_cost_item(ifc_file, schedule, name, identification, applied_value, unit_of_measurement, element_id):
    try:
        # Create a cost item under the existing schedule
        cost_item = ifcopenshell.api.run("cost.add_cost_item", ifc_file, cost_schedule=schedule)
        print(f"Created cost item: {cost_item}")

        # Edit cost item attributes
        ifcopenshell.api.run("cost.edit_cost_item", ifc_file, cost_item=cost_item, attributes={"Name": name, "Identification": identification})
        print(f"Edited cost item: {cost_item}")

        # Add a cost value for the current row
        value = ifcopenshell.api.run("cost.add_cost_value", ifc_file, parent=cost_item)
        print(f"Added cost value: {value}")

        # Edit cost value attributes
        ifcopenshell.api.run("cost.edit_cost_value", ifc_file, cost_value=value, attributes={"AppliedValue": applied_value})
        print(f"Edited cost value: {value}")

        # Find the element by its GlobalId
        element = ifc_file.by_guid(element_id)
        if not element:
            print(f"Element with GlobalId {element_id} not found")
            return

        print(f"Found element: {element}")

        # Assign the control (cost item) to the element
        ifcopenshell.api.run("control.assign_control", ifc_file, relating_control=cost_item, related_object=element)
        print(f"Assigned control: {cost_item} to element: {element}")

        # Extract quantities from the element
        qto_set_name = f"Qto_{element.is_a().replace('Ifc', '')}BaseQuantities"
        qto_sets = ifcopenshell.util.element.get_psets(element)
        qto_set = qto_sets.get(qto_set_name, {})
        
        volume = qto_set.get("NetVolume")
        area = qto_set.get("OuterSurfaceArea")

        print(f"Volume: {volume}, Area: {area}")

        # Optionally, assign quantity based on unit of measurement
        if unit_of_measurement == 'm3' and volume is not None:
            quantity = ifcopenshell.api.run("cost.add_cost_item_quantity", ifc_file, cost_item=cost_item, ifc_class="IfcQuantityVolume")
            ifcopenshell.api.run("cost.edit_cost_item_quantity", ifc_file, physical_quantity=quantity, attributes={"VolumeValue": float(volume)})
            print(f"Assigned volume quantity: {quantity} to cost item: {cost_item}")
        elif unit_of_measurement == 'm2' and area is not None:
            quantity = ifcopenshell.api.run("cost.add_cost_item_quantity", ifc_file, cost_item=cost_item, ifc_class="IfcQuantityArea")
            ifcopenshell.api.run("cost.edit_cost_item_quantity", ifc_file, physical_quantity=quantity, attributes={"AreaValue": float(area)})
            print(f"Assigned area quantity: {quantity} to cost item: {cost_item}")
        else:
            print(f"Unknown unit of measurement '{unit_of_measurement}' or missing quantity for element: {element}")

    except Exception as e:
        print(f"Error creating cost item: {e}")

# File path to the IFC file
ifc_file_path = r'C:\Users\shobh\OneDrive - Universidade do Minho\Fraunhofer\4D Using IFC SCHEMA\Model\Test_1_Task.ifc'

# File path to the CSV file containing BOL codes
csv_file_path = r"C:\Users\shobh\OneDrive - Universidade do Minho\Fraunhofer\IfcCostItem Implementation\Final Test\Tasks\Pricelist.csv"

# Call the open_ifc_file function to extract data
extracted_data = open_ifc_file(ifc_file_path)

# Open the IFC file
ifc_file = ifcopenshell.open(ifc_file_path)

# Call the search_bol_code function to search and match BOL codes
search_bol_code(csv_file_path, extracted_data)

# Create a cost schedule
schedule = ifcopenshell.api.run("cost.add_cost_schedule", ifc_file)
    
# Edit the cost schedule attributes (e.g., name)
ifcopenshell.api.run("cost.edit_cost_schedule", ifc_file, cost_schedule=schedule, attributes={"Name": "Cost Estimation"})

# Assuming extracted_data contains the required information
for data in extracted_data:
    for match in data.get("Matches", []):
        bol_code = match["BolCode"]
        description = match["Description"]
        price = match["Price"]
        unit_of_measurement = match["UnitOfMeasurement"]
        element_id = data["IfcGuid"]

        # Create cost item with description as name and bol_code as identification
        create_cost_item(ifc_file, schedule, name=description, identification=bol_code, applied_value=price, unit_of_measurement=unit_of_measurement, element_id=element_id)
print("Cost items created successfully.")

# Optionally, you can print or further process extracted_data or the created cost items.
print(extracted_data)
ifc_file.write(r"C:\Users\shobh\OneDrive - Universidade do Minho\Fraunhofer\4D Using IFC SCHEMA\Model\Test_1_Task+cost.ifc")