import json
from datetime import datetime

def load_json(filename):
	try:
		with open(filename, 'r') as f:
			return json.load(f)
	except FileNotFoundError:
		# File doesn't exist yet, return empty dict
		return {}

def save_json(filename, data):
	with open(filename, 'w') as f:
		json.dump(data, f, indent=2)


# --- Pricing Functions ---

def calculate_fee(mall_key, duration_hours):
# Round up hours to next whole number
	hours = int(duration_hours) if duration_hours == int(duration_hours) else int(duration_hours) + 1

	if mall_key == "1":  # Gateway Theatre of Shopping - flat rate R15
		fee = 15.0

	elif mall_key == "2":  # Pavilion Shopping Centre - R10 per hour
		fee = hours * 10.0

	elif mall_key == "3":  # La Lucia Mall - R12 per hour capped at R60
		fee = hours * 12.0
		if fee > 60.0:
			fee = 60.0

	else:
		fee = 0.0
	return fee

# --- Mall Definitions ---

MALLS = {
	"1": {
		"name": "Gateway Theatre of Shopping",
		"capacity": 250
	},
	"2": {
		"name": "Pavilion Shopping Centre",
		"capacity": 180
	},
	"3": {
		"name": "La Lucia Mall",
		"capacity": 150
	}
}

# --- User Management ---

USERS_FILE = "users.json"
PARKING_FILE = "parking.json"
PAYMENTS_FILE = "payments.json"

def load_users():
	return load_json(USERS_FILE)

def save_users(users):
	save_json(USERS_FILE, users)

def register_user():
	users = load_users()
	print("\n--- Register New User ---")
	username = input("Enter username: ").strip()
	if username in users:
		print("Username already exists.")
		return
	password = input("Enter password: ").strip()
	print("Select role:")
	print("1. Customer (Driver)")
	print("2. Parking Administrator")
	print("3. Owner/Shareholder")
	role_choice = input("Enter role number: ").strip()
	roles = {"1": "customer", "2": "admin", "3": "owner"}
	role = roles.get(role_choice)
	if not role:
		print("Invalid role selected.")
		return
	users[username] = {"password": password, "role": role}
	save_users(users)
	print(f"User '{username}' registered successfully as {role}.")

def login():
	users = load_users()
	print("\n--- Login ---")
	username = input("Username: ").strip()
	password = input("Password: ").strip()
	user = users.get(username)
	if not user or user["password"] != password:
		print("Invalid username or password.")
		return None
	print(f"Welcome, {username}! Role: {user['role']}")
	return {"username": username, "role": user["role"]}

# --- Parking Data Management ---

def load_parking():
	return load_json(PARKING_FILE)

def save_parking(parking):
	save_json(PARKING_FILE, parking)

def load_payments():
	return load_json(PAYMENTS_FILE)

def save_payments(payments):
	save_json(PAYMENTS_FILE, payments)

# --- Helper Functions ---

def select_mall():
	print("\nSelect a mall:")
	for key, mall in MALLS.items():
		print(f"{key}. {mall['name']} (Capacity: {mall['capacity']})")
	choice = input("Enter mall number: ").strip()
	mall = MALLS.get(choice)
	if not mall:
		print("Invalid mall selection.")
		return None, None
	print(f"Selected mall: {mall['name']}")
	return choice, mall

def current_parked_vehicles(parking_data, mall_key):
	# Returns dict vehicle_id -> entry_time for vehicles currently parked in mall
	return {vehicle_id: datetime.fromisoformat(info["entry_time"]) 
	for vehicle_id, info in parking_data.items() if info["mall"] == mall_key and not info["exit_time"]}

def vehicle_entry(user, mall_key, mall):
	parking_data = load_parking()
	parked = current_parked_vehicles(parking_data, mall_key)
	if len(parked) >= mall["capacity"]:
		print("Mall is full! Cannot allow entry.")
		return
	vehicle_id = input("Enter your vehicle registration number: ").strip()
	# Check if vehicle already parked
	if vehicle_id in parked:
			print("This vehicle is already parked in the mall.")
			return
	entry_time = datetime.now().isoformat()
	parking_data[vehicle_id] = {
		"user": user["username"],
		"mall": mall_key,
		"entry_time": entry_time,
		"exit_time": None,
		"paid": False
	}
	save_parking(parking_data)
	print(f"Vehicle {vehicle_id} entered at {entry_time}.")

def vehicle_exit(user, mall_key, _):
	parking_data = load_parking()
	payments = load_payments()
	vehicle_id = input("Enter your vehicle registration number: ").strip()
	record = parking_data.get(vehicle_id)
	if not record or record["mall"] != mall_key or record["exit_time"] is not None:
		print("Vehicle not found or already exited.")
		return
	if record["user"] != user["username"] and user["role"] != "admin" and user["role"] != "owner":
		print("You can only exit your own vehicle.")
		return
	entry_time = datetime.fromisoformat(record["entry_time"])
	exit_time = datetime.now()
	duration = (exit_time - entry_time).total_seconds() / 3600  # hours
	fee = calculate_fee(mall_key, duration)
	print(f"Parking duration: {duration:.2f} hours")
	print(f"Parking fee: R{fee:.2f}")
	confirm = input("Confirm payment? (y/n): ").strip().lower()
	if confirm != 'y':
		print("Payment cancelled.")
		return
	
 # Update parking record
	record["exit_time"] = exit_time.isoformat()
	record["paid"] = True
	parking_data[vehicle_id] = record
	save_parking(parking_data)
	
 # Record payment
	payment_id = f"{vehicle_id}_{exit_time.isoformat()}"
	payments[payment_id] = {
		"vehicle_id": vehicle_id,
		"mall": mall_key,
		"user": record["user"],
		"amount": fee,
		"timestamp": exit_time.isoformat()
	}
	save_payments(payments)
	print(f"Payment of R{fee:.2f} received. Thank you!")

def view_customer_history(user):
	parking_data = load_parking()
	payments = load_payments()
	print(f"\n--- Parking History for {user['username']} ---")
	for vehicle_id, record in parking_data.items():
		if record["user"] == user["username"]:
			entry = record["entry_time"]
			exit_ = record["exit_time"] or "Still parked"
			paid = "Yes" if record["paid"] else "No"
			print(f"Vehicle: {vehicle_id} | Mall: {MALLS[record['mall']]['name']} | Entry: {entry} | Exit: {exit_} | Paid: {paid}")
	print(f"\n--- Payment History for {user['username']} ---")
	for _, payment in payments.items():
		if payment["user"] == user["username"]:
			print(f"Vehicle: {payment['vehicle_id']} | Mall: {MALLS[payment['mall']]['name']} | Amount: R{payment['amount']:.2f} | Date: {payment['timestamp']}")

def admin_view_parked_vehicles(user):
	parking_data = load_parking()
	mall_key, mall = select_mall()
	if not mall:
		return
	print(f"\nVehicles currently parked at {mall['name']}:")
	count = 0
	for vehicle_id, record in parking_data.items():
		if record["mall"] == mall_key and record["exit_time"] is None:
				print(f"Vehicle: {vehicle_id} | User: {record['user']} | Entry: {record['entry_time']}")
				count += 1
	print(f"Total parked vehicles: {count}")
	print(f"Parking capacity: {mall['capacity']}")

def admin_view_daily_activity(user):
	parking_data = load_parking()
	mall_key, mall = select_mall()
	if not mall:
		return
	today = datetime.now().date()
	entries_today = 0
	exits_today = 0
	for record in parking_data.values():
		entry_date = datetime.fromisoformat(record["entry_time"]).date()
		exit_time = record["exit_time"]
		exit_date = datetime.fromisoformat(exit_time).date() if exit_time else None
		if record["mall"] == mall_key:
			if entry_date == today:
				entries_today += 1
			if exit_date == today:
				exits_today += 1
	print(f"\nDaily activity for {mall['name']} on {today}:")
	print(f"Entries today: {entries_today}")
	print(f"Exits today: {exits_today}")

def owner_generate_reports(_):
	parking_data = load_parking()
	payments = load_payments()
	print("\n--- Mall Reports ---")
	for mall_key, mall in MALLS.items():
		total_vehicles = sum(1 for r in parking_data.values() if r["mall"] == mall_key)
		total_revenue = sum(p["amount"] for p in payments.values() if p["mall"] == mall_key)
		durations = []
		for r in parking_data.values():
			if r["mall"] == mall_key and r["exit_time"]:
				entry = datetime.fromisoformat(r["entry_time"])
				exit_ = datetime.fromisoformat(r["exit_time"])
				durations.append((exit_ - entry).total_seconds() / 3600)
		avg_duration = sum(durations)/len(durations) if durations else 0
		print(f"\nMall: {mall['name']}")
		print(f"Total vehicles parked: {total_vehicles}")
		print(f"Total revenue: R{total_revenue:.2f}")
		print(f"Average parking duration: {avg_duration:.2f} hours")

def customer_menu(user):
	mall_key, mall = select_mall()
	if not mall:
		return
	while True:
		print(f"\n--- Customer Menu ({mall['name']}) ---")
		print("1. Register Vehicle Entry")
		print("2. Register Vehicle Exit")
		print("3. View Parking and Payment History")
		print("4. Change Mall")
		print("5. Logout")
		choice = input("Choose an option: ").strip()
		if choice == '1':
			vehicle_entry(user, mall_key, mall)
		elif choice == '2':
			vehicle_exit(user, mall_key, mall)
		elif choice == '3':
			view_customer_history(user)
		elif choice == '4':
			mall_key, mall = select_mall()
			if not mall:
				return
		elif choice == '5':
			print("Logging out...")
			break
		else:
			print("Invalid choice.")

def admin_menu(user):
	while True:
		print("\n--- Parking Administrator Menu ---")
		print("1. View Vehicles Currently Parked")
		print("2. View Daily Parking Activity")
		print("3. Logout")
		choice = input("Choose an option: ").strip()
		if choice == '1':
			admin_view_parked_vehicles(user)
		elif choice == '2':
			admin_view_daily_activity(user)
		elif choice == '3':
			print("Logging out...")
			break
		else:
			print("Invalid choice.")

def owner_menu(user):
	while True:
		print("\n--- Owner/Shareholder Menu ---")
		print("1. Generate and View Reports")
		print("2. Logout")
		choice = input("Choose an option: ").strip()
		if choice == '1':
			owner_generate_reports(user)
		elif choice == '2':
			print("Logging out...")
			break
		else:
			print("Invalid choice.")

def main():
	print("=== Welcome to the KwaZulu-Natal Parking Management System ===")
	while True:
		print("\nMain Menu:")
		print("1. Register")
		print("2. Login")
		print("3. Exit")
		choice = input("Choose an option: ").strip()
		if choice == '1':
			register_user()
		elif choice == '2':
			user = login()
			if user:
				if user["role"] == "customer":
					customer_menu(user)
				elif user["role"] == "admin":
					admin_menu(user)
				elif user["role"] == "owner":
					owner_menu(user)
		elif choice == '3':
			print("Goodbye!")
			break
		else:
			print("Invalid choice.")

if __name__ == "__main__":
	main()