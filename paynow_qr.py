import qrcode
import struct
import binascii

class PayNowQR:
    def __init__(self, proxy_value, amount, recipient_name, proxy_type='MOBILE'):
        """
        :param proxy_value: The mobile number (e.g., '+6591234567') or UEN.
        :param amount: The amount to receive (e.g., 10.50).
        :param recipient_name: The name displayed to the payer (max 25 chars recommended).
        :param proxy_type: 'MOBILE' or 'UEN'.
        """
        self.proxy_value = proxy_value
        self.amount = "{:.2f}".format(float(amount))
        self.name = recipient_name.upper()
        self.proxy_type = '0' if proxy_type.upper() == 'MOBILE' else '2'

    def _generate_crc16(self, payload):
        """Calculates the CRC16-CCITT (0xFFFF) checksum required by SGQR."""
        crc = 0xFFFF
        polynomial = 0x1021
        
        for char in payload:
            byte = ord(char)
            for i in range(8):
                bit = (byte >> (7 - i) & 1) == 1
                c15 = (crc >> 15 & 1) == 1
                crc <<= 1
                if c15 ^ bit:
                    crc ^= polynomial
        
        crc &= 0xFFFF
        return "{:04X}".format(crc)

    def _format_field(self, field_id, value):
        """Formats data into TLV (Tag-Length-Value) format."""
        value_str = str(value)
        length = len(value_str)
        return f"{field_id}{length:02}{value_str}"

    def generate_payload(self):
        # 1. Payload Format Indicator (00) & Point of Initiation (01)
        # '12' = Dynamic (use for specific amounts), '11' = Static
        root = self._format_field("00", "01") + self._format_field("01", "12")

        # 2. Merchant Account Information (26 - PayNow)
        merchant_info = (
            self._format_field("00", "SG.PAYNOW") +
            self._format_field("01", self.proxy_type) +
            self._format_field("02", self.proxy_value) +
            self._format_field("03", "0") +  # 0 = Amount not editable, 1 = Editable
            self._format_field("04", "20991231")  # Expiry date (required by some apps)
        )
        root += self._format_field("26", merchant_info)

        # 3. Merchant Category Code (52) - 0000 for General
        root += self._format_field("52", "0000")

        # 4. Transaction Currency (53) - 702 is SGD
        root += self._format_field("53", "702")

        # 5. Transaction Amount (54)
        root += self._format_field("54", self.amount)

        # 6. Country Code (58)
        root += self._format_field("58", "SG")

        # 7. Merchant Name (59)
        root += self._format_field("59", self.name)

        # 8. Merchant City (60)
        root += self._format_field("60", "Singapore")

        # 9. CRC Checksum (63)
        # We append the ID and length first, then calculate CRC over the whole string
        root += "6304" 
        crc = self._generate_crc16(root)
        
        return root + crc

    def save_qr(self, filename="paynow.png"):
        payload = self.generate_payload()
        print(f"Generated Payload: {payload}")
        
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=4,
        )
        qr.add_data(payload)
        qr.make(fit=True)

        img = qr.make_image(fill_color="purple", back_color="white")
        img.save(filename)
        print(f"Success! QR code saved as {filename}")

# --- USAGE ---
if __name__ == "__main__":
    print("--- PayNow QR Generator ---")
    
    # Get user input
    mobile_input = input("Enter Mobile Number (e.g., 91234567): ").strip()
    # Add +65 if missing (simple check)
    if not mobile_input.startswith('+'):
        mobile_input = '+65' + mobile_input
        
    amount_input = input("Enter Amount (e.g., 18.50): ").strip()
    name_input = input("Enter Recipient Name (e.g., J SMITH): ").strip()

    # Create and save QR
    my_qr = PayNowQR(
        proxy_value=mobile_input, 
        amount=amount_input, 
        recipient_name=name_input
    )

    my_qr.save_qr()
