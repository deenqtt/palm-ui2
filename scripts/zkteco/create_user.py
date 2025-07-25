#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import json
import os
from zk import ZK
from zk.user import User

# Set UTF-8 encoding for Windows
if os.name == 'nt':  # Windows
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.detach())
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.detach())

def get_existing_uids(conn):
    """Get all existing UIDs from the device"""
    try:
        users = conn.get_users()
        existing_uids = [user.uid for user in users]
        print(f"[INFO] Found {len(existing_uids)} existing users with UIDs: {sorted(existing_uids)}")
        return existing_uids
    except Exception as e:
        print(f"[WARNING] Could not get existing users: {str(e)}")
        return []

def find_next_sequential_uid(conn, preferred_uid):
    """Find the next sequential UID, continuing from the highest existing UID"""
    existing_uids = get_existing_uids(conn)
    
    if not existing_uids:
        # No existing users, start from preferred UID or 1
        next_uid = max(1, preferred_uid)
        print(f"[INFO] No existing users, starting from UID {next_uid}")
        return next_uid
    
    # Get the highest existing UID
    max_existing_uid = max(existing_uids)
    
    # If preferred UID is higher than max existing and available, use it
    if preferred_uid > max_existing_uid and preferred_uid not in existing_uids:
        print(f"[INFO] Using preferred UID {preferred_uid} (higher than max existing {max_existing_uid})")
        return preferred_uid
    
    # Otherwise, use next sequential UID after the highest existing
    next_uid = max_existing_uid + 1
    
    # Make sure the next UID is not taken (safety check)
    while next_uid in existing_uids and next_uid < 65535:
        next_uid += 1
    
    if next_uid >= 65535:
        raise Exception("Maximum UID limit reached (65535)")
    
    print(f"[INFO] Using next sequential UID {next_uid} (after max existing {max_existing_uid})")
    return next_uid

def create_user(ip, port, password, timeout, uid, name, user_id, privilege=0, user_password=None):
    try:
        print(f"[INFO] Connecting to ZKTeco device: {ip}:{port}")
        
        # Create ZK instance
        device_password = int(password) if password != 'None' and password.isdigit() else 0
        zk = ZK(ip, port=int(port), timeout=int(timeout), password=device_password)
        
        # Connect to device
        conn = zk.connect()
        print(f"[SUCCESS] Connected to ZKTeco device successfully")
        
        # Find next sequential UID
        preferred_uid = int(uid)
        sequential_uid = find_next_sequential_uid(conn, preferred_uid)
        
        # Ensure all parameters are correct types with proper validation
        final_uid = int(sequential_uid)
        final_privilege = int(privilege) if privilege else 0
        final_password = str(user_password) if user_password else ""
        final_name = str(name)[:24]  # ZKTeco name limit is 24 characters
        
        # IMPORTANT: user_id should be a string, not an integer
        # But it should contain only numeric characters for ZKTeco compatibility
        final_user_id = str(user_id).strip()
        
        # Validate that user_id contains only digits (ZKTeco requirement)
        if not final_user_id.isdigit():
            raise ValueError(f"user_id must contain only digits, got: {final_user_id}")
        
        print(f"[INFO] Creating user: UID={final_uid}, Name={final_name}, UserID={final_user_id}, Privilege={final_privilege}")
        print(f"[DEBUG] Data types: UID={type(final_uid)}, Name={type(final_name)}, UserID={type(final_user_id)}, Privilege={type(final_privilege)}")
        
        # Create user object with proper data types
        # Note: ZKTeco User constructor expects specific types
        user = User(
            uid=final_uid,           # int
            name=final_name,         # str
            privilege=final_privilege, # int
            password=final_password,  # str
            group_id="1",            # str (empty string is fine)
            user_id=final_user_id,   # str (but numeric content)
            card=0                   # int (no card initially)
        )
        
        print(f"[DEBUG] User object created successfully")
        
        # Set user to device
        conn.set_user(user)
        print(f"[SUCCESS] User created successfully with UID {final_uid}")
        
        # Verify user was created by getting it back
        try:
            created_user = conn.get_user(uid=final_uid)
            if created_user:
                print(f"[VERIFY] User verified on device: UID={created_user.uid}, Name={created_user.name}")
            else:
                print(f"[WARNING] Could not verify user creation")
        except Exception as verify_error:
            print(f"[WARNING] Could not verify user creation: {str(verify_error)}")
        
        # Disconnect
        conn.disconnect()
        print(f"[SUCCESS] Connection closed")
        
        result = {
            "success": True,
            "message": f"User {final_name} created successfully",
            "user": {
                "uid": final_uid,
                "name": final_name,
                "user_id": final_user_id,
                "privilege": final_privilege,
                "original_uid": int(uid),
                "uid_changed": final_uid != int(uid)
            }
        }
        
        print(json.dumps(result))
        return True
        
    except Exception as e:
        print(f"[ERROR] Error creating user: {str(e)}")
        print(f"[ERROR] Error type: {type(e).__name__}")
        
        # More detailed error information
        import traceback
        print(f"[ERROR] Traceback: {traceback.format_exc()}")
        
        error_result = {
            "success": False,
            "error": str(e),
            "user": {"uid": uid, "name": name, "user_id": user_id},
            "error_type": type(e).__name__,
            "details": {
                "final_uid": final_uid if 'final_uid' in locals() else None,
                "final_name": final_name if 'final_name' in locals() else None,
                "final_user_id": final_user_id if 'final_user_id' in locals() else None,
                "final_privilege": final_privilege if 'final_privilege' in locals() else None
            }
        }
        print(json.dumps(error_result))
        return False

if __name__ == "__main__":
    if len(sys.argv) < 8:
        print(json.dumps({"success": False, "error": "Usage: python create_user.py <ip> <port> <password> <timeout> <uid> <name> <user_id> [privilege] [user_password]"}))
        sys.exit(1)
    
    ip = sys.argv[1]
    port = sys.argv[2]
    password = sys.argv[3]
    timeout = sys.argv[4]
    uid = sys.argv[5]
    name = sys.argv[6]
    user_id = sys.argv[7]
    privilege = sys.argv[8] if len(sys.argv) > 8 else 0
    user_password = sys.argv[9] if len(sys.argv) > 9 else None
    
    print(f"[DEBUG] Input arguments:")
    print(f"[DEBUG] IP: {ip}, Port: {port}, Password: {password}, Timeout: {timeout}")
    print(f"[DEBUG] UID: {uid} ({type(uid)}), Name: {name} ({type(name)}), UserID: {user_id} ({type(user_id)})")
    print(f"[DEBUG] Privilege: {privilege} ({type(privilege)}), Password: {user_password}")
    
    success = create_user(ip, port, password, timeout, uid, name, user_id, privilege, user_password)
    sys.exit(0 if success else 1)
