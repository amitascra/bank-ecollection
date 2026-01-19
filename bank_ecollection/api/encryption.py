# Copyright (c) 2026, Amit Kumar and contributors
# For license information, please see license.txt

import frappe
import json
import base64
import os
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5
from Crypto.Random import get_random_bytes


def encrypt_request(payload, settings):
	"""Encrypt request payload using ICICI public key"""
	try:
		# Convert payload to JSON string
		json_payload = json.dumps(payload, separators=(',', ':'))
		
		# Get public key
		public_key = load_public_key(settings.public_key_path)
		
		if not public_key:
			# Return unencrypted payload if no key configured
			frappe.logger().warning("No public key configured, sending unencrypted payload")
			return payload
		
		# Encrypt payload
		cipher = PKCS1_v1_5.new(public_key)
		encrypted_data = cipher.encrypt(json_payload.encode('utf-8'))
		
		# Base64 encode
		encrypted_b64 = base64.b64encode(encrypted_data).decode('utf-8')
		
		return {
			"encryptedData": encrypted_b64
		}
		
	except Exception as e:
		frappe.log_error(f"Encryption Error: {str(e)}")
		# Return original payload if encryption fails
		return payload


def decrypt_response(response_data, settings):
	"""Decrypt response from ICICI using private key"""
	try:
		# Check if response is encrypted
		if not isinstance(response_data, dict) or "encryptedData" not in response_data:
			# Return as-is if not encrypted
			return response_data
		
		# Get private key
		private_key = load_private_key(settings.private_key_path)
		
		if not private_key:
			frappe.logger().warning("No private key configured, cannot decrypt response")
			return response_data
		
		# Decrypt data
		encrypted_data = base64.b64decode(response_data["encryptedData"])
		cipher = PKCS1_v1_5.new(private_key)
		
		decrypted_data = cipher.decrypt(encrypted_data, None)
		
		if decrypted_data is None:
			raise Exception("Decryption failed")
		
		# Parse JSON
		return json.loads(decrypted_data.decode('utf-8'))
		
	except Exception as e:
		frappe.log_error(f"Decryption Error: {str(e)}")
		# Return original response if decryption fails
		return response_data


def load_public_key(key_path):
	"""Load RSA public key from file"""
	try:
		if not key_path or not os.path.exists(key_path):
			return None
		
		with open(key_path, 'r') as key_file:
			key_data = key_file.read()
		
		return RSA.import_key(key_data)
		
	except Exception as e:
		frappe.log_error(f"Public Key Load Error: {str(e)}")
		return None


def load_private_key(key_path):
	"""Load RSA private key from file"""
	try:
		if not key_path or not os.path.exists(key_path):
			return None
		
		with open(key_path, 'r') as key_file:
			key_data = key_file.read()
		
		return RSA.import_key(key_data)
		
	except Exception as e:
		frappe.log_error(f"Private Key Load Error: {str(e)}")
		return None


@frappe.whitelist()
def generate_key_pair():
	"""Generate RSA key pair for ICICI encryption"""
	try:
		# Generate 4096-bit RSA key pair
		key = RSA.generate(4096)
		
		# Get private and public keys
		private_key = key.export_key()
		public_key = key.publickey().export_key()
		
		# Create keys directory if it doesn't exist
		keys_dir = os.path.join(frappe.get_site_path(), "private", "files", "icici_keys")
		os.makedirs(keys_dir, exist_ok=True)
		
		# Save keys to files
		private_key_path = os.path.join(keys_dir, "icici_private_key.pem")
		public_key_path = os.path.join(keys_dir, "icici_public_key.pem")
		
		with open(private_key_path, 'wb') as f:
			f.write(private_key)
		
		with open(public_key_path, 'wb') as f:
			f.write(public_key)
		
		# Set proper permissions
		os.chmod(private_key_path, 0o600)
		os.chmod(public_key_path, 0o644)
		
		return {
			"success": True,
			"private_key_path": private_key_path,
			"public_key_path": public_key_path,
			"message": "RSA key pair generated successfully"
		}
		
	except Exception as e:
		frappe.log_error(f"Key Generation Error: {str(e)}")
		return {"success": False, "message": str(e)}


@frappe.whitelist()
def test_encryption():
	"""Test encryption/decryption functionality"""
	try:
		settings = frappe.get_single("ICICI Settings")
		
		# Test payload
		test_payload = {
			"test": "data",
			"timestamp": frappe.utils.now(),
			"amount": 1000.50
		}
		
		# Encrypt
		encrypted = encrypt_request(test_payload, settings)
		
		# Decrypt
		decrypted = decrypt_response({"encryptedData": encrypted.get("encryptedData")}, settings)
		
		# Verify
		if decrypted == test_payload:
			return {
				"success": True,
				"message": "Encryption/Decryption test successful",
				"original": test_payload,
				"decrypted": decrypted
			}
		else:
			return {
				"success": False,
				"message": "Encryption/Decryption test failed - data mismatch",
				"original": test_payload,
				"decrypted": decrypted
			}
		
	except Exception as e:
		frappe.log_error(f"Encryption Test Error: {str(e)}")
		return {"success": False, "message": str(e)}


def validate_key_pair(public_key_path, private_key_path):
	"""Validate that public and private keys are a matching pair"""
	try:
		public_key = load_public_key(public_key_path)
		private_key = load_private_key(private_key_path)
		
		if not public_key or not private_key:
			return False, "Could not load keys"
		
		# Test encryption/decryption
		test_data = b"test_validation_data"
		
		# Encrypt with public key
		cipher_encrypt = PKCS1_v1_5.new(public_key)
		encrypted = cipher_encrypt.encrypt(test_data)
		
		# Decrypt with private key
		cipher_decrypt = PKCS1_v1_5.new(private_key)
		decrypted = cipher_decrypt.decrypt(encrypted, None)
		
		if decrypted == test_data:
			return True, "Key pair is valid"
		else:
			return False, "Key pair validation failed"
		
	except Exception as e:
		return False, f"Key validation error: {str(e)}"


def get_key_info(key_path):
	"""Get information about RSA key"""
	try:
		if not os.path.exists(key_path):
			return {"exists": False}
		
		with open(key_path, 'r') as f:
			key_data = f.read()
		
		key = RSA.import_key(key_data)
		
		return {
			"exists": True,
			"size": key.size_in_bits(),
			"has_private": key.has_private(),
			"created": os.path.getctime(key_path),
			"modified": os.path.getmtime(key_path)
		}
		
	except Exception as e:
		return {"exists": False, "error": str(e)}


@frappe.whitelist()
def get_encryption_status():
	"""Get current encryption configuration status"""
	try:
		settings = frappe.get_single("ICICI Settings")
		
		public_key_info = get_key_info(settings.public_key_path) if settings.public_key_path else {"exists": False}
		private_key_info = get_key_info(settings.private_key_path) if settings.private_key_path else {"exists": False}
		
		# Validate key pair if both exist
		key_pair_valid = False
		if public_key_info.get("exists") and private_key_info.get("exists"):
			key_pair_valid, validation_msg = validate_key_pair(settings.public_key_path, settings.private_key_path)
		else:
			validation_msg = "Keys not configured"
		
		return {
			"success": True,
			"public_key": public_key_info,
			"private_key": private_key_info,
			"key_pair_valid": key_pair_valid,
			"validation_message": validation_msg,
			"encryption_enabled": public_key_info.get("exists", False) and private_key_info.get("exists", False)
		}
		
	except Exception as e:
		frappe.log_error(f"Encryption Status Error: {str(e)}")
		return {"success": False, "message": str(e)}
