# Script to convert KSU CAN log format to candump format
def convert_can_logs(input_file, output_file):
    with open(input_file, 'r') as f_in, open(output_file, 'w') as f_out:
        for line in f_in:
            parts = line.strip().split(',')
            timestamp_sec = float(parts[0]) / 1000  # Convert milliseconds to seconds
            msg_id = parts[1]
            msg_len = int(parts[2])
            data = parts[3]

            # Convert message ID and length to hexadecimal format
            msg_id_hex = f'{int(msg_id, 16):X}'
            msg_len_hex = f'{msg_len:X}'

            # Modify the format of the data section
            data_formatted = data

            # Write the converted log entry to the output file
            f_out.write(f'({timestamp_sec:.6f}) can0 {msg_id_hex.zfill(3)}#{data_formatted}\n')

# Example usage
input_file = 'MDY_10-24-2023_HMS_21-50-53.CSV'
output_file = 'can_logs_output.log'
convert_can_logs(input_file, output_file)
