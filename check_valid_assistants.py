# check_valid_assistants.py

from db.connection import get_connection

def check_valid_assistants():
    """Check valid assistant users."""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Get users with assistant role
        cursor.execute("""
            SELECT id, username, id_role
            FROM user
            WHERE id_role = 3 OR username LIKE 'assistant%'
            ORDER BY id
        """)
        assistants = cursor.fetchall()

        print(f"\n=== Valid Assistant Users ===")
        if assistants:
            for assistant in assistants:
                print(f"  ID: {assistant['id']}, Username: {assistant['username']}, Role: {assistant['id_role']}")
        else:
            print("  No assistant users found")

        # Get all users for reference
        cursor.execute("SELECT id, username, id_role FROM user ORDER BY id")
        all_users = cursor.fetchall()

        print(f"\n=== All Users ===")
        for user in all_users:
            role_name = "Unknown"
            if user['id_role'] == 1:
                role_name = "Admin"
            elif user['id_role'] == 2:
                role_name = "Lecturer"
            elif user['id_role'] == 3:
                role_name = "Assistant"
            print(f"  ID: {user['id']}, Username: {user['username']}, Role: {role_name}")

        cursor.close()
        conn.close()

    except Exception as e:
        print(f"Error checking assistants: {str(e)}")

if __name__ == "__main__":
    check_valid_assistants()