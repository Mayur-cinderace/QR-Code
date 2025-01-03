import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# Google Sheet URL
google_sheet_url = "https://docs.google.com/spreadsheets/d/1XEJUuvDAuWzzjKxgYhAUVi6jDxugTx0Gvn8NyvVZ1w8/edit?gid=1470509049#gid=1470509049"  # Your Google Sheet URL
SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']

# Load Google Sheet using Streamlit secrets
def load_google_sheet(sheet_url):
    try:
        # Fetch the credentials from Streamlit secrets
        credentials_info = st.secrets["google_credentials"]
        
        # Convert the credentials from the secrets into a Credentials object
        credentials = Credentials.from_service_account_info(credentials_info, scopes=SCOPES)

        # Authorize the Google Sheets API client
        gc = gspread.authorize(credentials)

        # Open the spreadsheet and get the first sheet
        spreadsheet = gc.open_by_url(sheet_url)
        sheet = spreadsheet.sheet1  # Access the first sheet

        # Get all records from the sheet and convert them into a pandas DataFrame
        data = pd.DataFrame(sheet.get_all_records())
        return sheet, data
    except Exception as e:
        st.error(f"Error loading Google Sheet: {e}")
        return None, pd.DataFrame()

# Update Google Sheet
def update_google_sheet(sheet, updated_data):
    try:
        sheet.clear()  # Clear existing data
        sheet.update([updated_data.columns.values.tolist()] + updated_data.values.tolist())
        st.success("Google Sheet updated successfully!")
    except Exception as e:
        st.error(f"Error updating Google Sheet: {e}")

# Streamlit interface
st.title("Pharmacy Inventory Management")

# Load data from Google Sheet initially
sheet, data = load_google_sheet(google_sheet_url)

if not data.empty:
    # Display the initial inventory table
    st.subheader("Available Medicines")
    medicines_table = st.empty()  # Placeholder for the inventory table
    medicines_table.write(data[['Medicine Name', 'Supplier Name', 'Stock', 'Expiry Date', 'Price per Unit']])

    # Order Section
    st.subheader("Place an Order")

    # Select Supplier
    supplier_name = st.selectbox("Select Supplier Name", options=data['Supplier Name'].unique())

    # Filter data for the selected supplier
    supplier_data = data[data['Supplier Name'] == supplier_name]

    # Sort medicines based on expiry date (earlier expiry first)
    supplier_data = supplier_data.sort_values(by='Expiry Date')

    # Select Medicines
    ordered_medicines = st.multiselect("Select Medicines to Order", options=supplier_data['Medicine Name'].unique())

    if ordered_medicines:
        order_details = []
        for medicine in ordered_medicines:
            # Fetch stock and price for the selected supplier and medicine
            stock_row = supplier_data[supplier_data['Medicine Name'] == medicine]
            max_quantity = int(stock_row['Stock'].iloc[0])
            price_per_unit = float(stock_row['Price per Unit'].iloc[0])

            st.write(f"Available stock for {medicine} from {supplier_name}: {max_quantity}")
            quantity = st.number_input(f"Enter quantity for {medicine}", min_value=0, max_value=max_quantity, step=1)
            if quantity > 0:
                order_details.append({
                    "Medicine Name": medicine,
                    "Quantity": quantity,
                    "Price per Unit": price_per_unit,
                    "Total Price": quantity * price_per_unit,
                    "Row Index": stock_row.index[0]  # Keep track of the row index for updates
                })

        # Generate Bill
        if order_details:
            order_df = pd.DataFrame(order_details)
            st.subheader("Order Summary")
            st.write(order_df)
            total_amount = order_df['Total Price'].sum()
            st.write(f"**Total Amount: ₹{total_amount:.2f}**")

            # Confirm and Update
            if st.button("Confirm Order"):
                # Update stock in the data and Google Sheet
                for order in order_details:
                    row_index = order["Row Index"]
                    quantity_ordered = order["Quantity"]

                    # Update the specific row in the dataframe
                    data.at[row_index, 'Stock'] -= quantity_ordered

                # Update the Google Sheet with the new data
                update_google_sheet(sheet, data)

                # Update the inventory table shown in the UI
                medicines_table.write(data[['Medicine Name', 'Supplier Name', 'Stock', 'Expiry Date', 'Price per Unit']])

                st.success(f"Order placed and inventory updated for supplier: {supplier_name}")
