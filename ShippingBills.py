from kivy.app import App
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.scrollview import ScrollView
from kivy.uix.popup import Popup
from kivy.uix.gridlayout import GridLayout  # Importa GridLayout
from kivy.core.window import Window
from kivy.uix.widget import Widget
from kivy.graphics import Color, Rectangle
from PIL import Image, ImageDraw, ImageFont
import os
from datetime import datetime
import csv
import pywhatkit as kit
from kivy.core.text import LabelBase
import sqlite3
from kivy.uix.spinner import Spinner
from kivy.uix.dropdown import DropDown
from kivy.uix.spinner import SpinnerOption
import textwrap

class MyApp(App):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.db_path = "recibos.db"  # Nombre del archivo de la base de datos
        self.is_edit_mode = False  # Bandera para rastrear si estamos en modo de edición
        self.editing_sender_phone = None  # ID del recibo que se está editando
        self.init_database()

    def init_database(self):
        """Initialize the database and create the table if it doesn't exist."""
        connection = sqlite3.connect(self.db_path)
        cursor = connection.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS recibos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                shipper TEXT,
                address TEXT,
                phone TEXT,
                shippee TEXT,
                destination TEXT,
                recipient_id TEXT,
                recipient_phone TEXT,
                weight REAL,
                length REAL,
                width REAL,
                height REAL,
                subtotal REAL,
                discount REAL,
                total REAL,
                cash REAL,
                card REAL,
                shipping_code TEXT,
                date TEXT
            )
        """)
        connection.commit()
        connection.close()

    def build(self):
        # Set the app title
        self.title = "Shipping Bills"

        # Set the app icon
        icon_path = os.path.join(os.getcwd(), "app.png")
        if os.path.exists(icon_path):
            Window.set_icon(icon_path)
        else:
            print("Warning: app.png not found. Default icon will be used.")

        # Set the app to open in fullscreen
        Window.maximize()

        # Set background color to light brown
        root = BoxLayout(orientation='vertical')
        with root.canvas.before:
            Color(0.82, 0.71, 0.55, 1)  # RGB for light brown
            self.rect = Rectangle(size=Window.size, pos=root.pos)
            root.bind(size=self._update_rect, pos=self._update_rect)

        # Main layout with ScrollView
        scroll_view = ScrollView(size_hint=(1, None), size=(Window.width, Window.height))
        layout = BoxLayout(orientation='vertical', spacing=20, padding=20, size_hint_y=None)
        layout.bind(minimum_height=layout.setter('height'))

        # Helper function to create smaller and more readable TextInput
        def create_text_input(hint_text, next_input=None):
            text_input = TextInput(hint_text=hint_text, multiline=False, size_hint=(1, None), height=40, font_size=16)
            if next_input:
                text_input.bind(on_text_validate=lambda instance: setattr(next_input, 'focus', True))
            return text_input

        # Create sections for better organization
        def create_section(title, fields, next_section_first_input=None):
            section = BoxLayout(orientation='vertical', spacing=10, padding=10, size_hint_y=None)
            section.add_widget(Label(text=title, bold=True, font_size=20, size_hint=(1, None), height=40))
            previous_input = None
            for i, field in enumerate(fields):
                row = BoxLayout(orientation='horizontal', spacing=10, size_hint_y=None, height=50)
                row.add_widget(Label(text=field['label'], font_size=16, size_hint=(0.5, None), height=40))
                # If it's the last field in the section, link it to the next section's first input
                next_input = None
                if i == len(fields) - 1 and next_section_first_input:
                    next_input = next_section_first_input
                text_input = create_text_input(field['hint'], next_input=next_input)
                if previous_input:
                    previous_input.bind(on_text_validate=lambda instance, next_input=text_input: setattr(next_input, 'focus', True))
                setattr(self, field['name'], text_input)
                row.add_widget(text_input)
                section.add_widget(row)
                previous_input = text_input
            section.height = len(fields) * 60 + 50
            return section

        # Sender information
        sender_section = create_section("Sender Information", [
            {'label': "Sender (Shipper):", 'hint': "Enter sender's name", 'name': 'shipper_input'},
            {'label': "Sender's Address:", 'hint': "Enter sender's address", 'name': 'address_input'},
            {'label': "Sender's Phone:", 'hint': "Enter sender's phone", 'name': 'phone_input'}
        ])

        # Define the first input of the recipient section before creating it
        self.shippee_input = TextInput(hint_text="Enter recipient's name", multiline=False, size_hint=(1, None), height=40, font_size=16)

        # Recipient information
        recipient_section = create_section("Recipient Information", [
            {'label': "Recipient (Shippee):", 'hint': "Enter recipient's name", 'name': 'shippee_input'},
            {'label': "Recipient's Address:", 'hint': "Enter recipient's address", 'name': 'destination_input'},
            {'label': "Recipient's ID:", 'hint': "Enter recipient's ID", 'name': 'recipient_id_input'},
            {'label': "Recipient's Phone:", 'hint': "Enter recipient's phone", 'name': 'recipient_phone_input'}
        ], next_section_first_input=self.shippee_input)

        # Define the first input of the shipping section before creating it
        self.weight_input = TextInput(hint_text="Enter weight in kg", multiline=False, size_hint=(1, None), height=40, font_size=16)

        # Shipping details
        shipping_section = BoxLayout(orientation='vertical', spacing=10, padding=10, size_hint_y=None)
        shipping_section.add_widget(Label(text="Shipping Details", bold=True, font_size=20, size_hint=(1, None), height=40))

        # Weight (TextInput)
        row_weight = BoxLayout(orientation='horizontal', spacing=10, size_hint_y=None, height=50)
        row_weight.add_widget(Label(text="Actual Weight (kg):", font_size=16, size_hint=(0.5, None), height=40))
        row_weight.add_widget(self.weight_input)  # Keep the existing TextInput for weight
        shipping_section.add_widget(row_weight)

        # Box Size (Spinner)
        row_box_size = BoxLayout(orientation='horizontal', spacing=10, size_hint_y=None, height=50)
        row_box_size.add_widget(Label(text="Box Size:", font_size=16, size_hint=(0.5, None), height=40))
        row_box_size.add_widget(self.create_box_size_spinner())  # Add the Spinner for box sizes
        shipping_section.add_widget(row_box_size)

        # Shipping Code (TextInput)
        row_shipping_code = BoxLayout(orientation='horizontal', spacing=10, size_hint_y=None, height=50)
        row_shipping_code.add_widget(Label(text="Shipping Code:", font_size=16, size_hint=(0.5, None), height=40))
        self.shipping_code_input = TextInput(hint_text="Enter shipping code", multiline=False, size_hint=(1, None), height=40, font_size=16)
        row_shipping_code.add_widget(self.shipping_code_input)  # Define the attribute here
        shipping_section.add_widget(row_shipping_code)

        shipping_section.height = 3 * 60 + 50

        # Define the first input of the totals section before creating it
        self.subtotal_input = TextInput(hint_text="Enter sub-total", multiline=False, size_hint=(1, None), height=40, font_size=16)

        # Totals and payment
        totals_section = create_section("Totals and Payment", [
            {'label': "Sub-Total:", 'hint': "Enter sub-total", 'name': 'subtotal_input'},
            {'label': "Discount:", 'hint': "Enter discount", 'name': 'discount_input'},
            {'label': "Total:", 'hint': "Enter total", 'name': 'total_input'},
            {'label': "Cash:", 'hint': "Enter cash amount", 'name': 'cash_input'},
            {'label': "Card:", 'hint': "Enter card amount", 'name': 'card_input'}
        ], next_section_first_input=self.subtotal_input)

        # Buttons
        buttons_section = BoxLayout(orientation='horizontal', spacing=20, padding=10, size_hint_y=None, height=70)

        buttons = [
            {"text": "Generate Receipt", "callback": self.generate_receipt},
            {"text": "Open Receipt", "callback": self.show_open_popup},
            {"text": "Edit Receipt", "callback": self.show_edit_popup},
            {"text": "Send via WhatsApp", "callback": self.show_whatsapp_popup},
            {"text": "Delete Recipient", "callback": self.show_delete_popup},
            {"text": "Monthly Report", "callback": self.show_monthly_report}  # New button
        ]

        for button in buttons:
            btn = Button(text=button["text"], size_hint=(1, None), height=50, font_size=18)
            btn.bind(on_press=button["callback"])
            buttons_section.add_widget(btn)

        # Add sections to the main layout
        layout.add_widget(sender_section)
        layout.add_widget(recipient_section)
        layout.add_widget(shipping_section)
        layout.add_widget(totals_section)
        layout.add_widget(buttons_section)

        # Add layout to ScrollView
        scroll_view.add_widget(layout)
        root.add_widget(scroll_view)

        return root

    def _update_rect(self, instance, value):
        self.rect.size = instance.size
        self.rect.pos = instance.pos

    def clear_text_inputs(self):
        """Clear all text input fields."""
        for attr_name in dir(self):
            attr = getattr(self, attr_name)
            if isinstance(attr, TextInput):
                attr.text = ""

    def get_value_or_na(self, value, is_numeric=False):
        """Return the value if it exists, otherwise return 'N/A' or 0.0 for numeric fields."""
        value = value.strip()
        if not value:
            return 0.0 if is_numeric else "N/A"
        if is_numeric:
            try:
                return float(value)
            except ValueError:
                return 0.0  # Default to 0.0 if the value is not a valid number
        return value

    def generate_receipt(self, instance):
        """Generate a receipt, save it to the database, and open the receipt image."""
        # Verificar si todos los campos están en blanco
        if not any([
            self.shipper_input.text.strip(),
            self.address_input.text.strip(),
            self.phone_input.text.strip(),
            self.shippee_input.text.strip(),
            self.destination_input.text.strip(),
            self.recipient_phone_input.text.strip(),
            self.recipient_phone_input.text.strip(),
            self.weight_input.text.strip(),
            self.subtotal_input.text.strip(),
            self.discount_input.text.strip(),
            self.total_input.text.strip(),
            self.cash_input.text.strip(),
            self.card_input.text.strip(),
            self.shipping_code_input.text.strip()
        ]):
            self.show_error_popup("Error:the phone number of the receipt cant be empty.")
            return

        # Extraer las dimensiones del Spinner
        box_size = self.box_size_spinner.text
        if (box_size == "Select Box Size"):
            self.show_error_popup("Error: Please select a box size.")
            return
        if box_size == "Irregular":
            length, width, height = 0, 0, 0  # Default values for irregular boxes
        else:
            try:
                length, width, height = map(int, box_size.split("x"))
            except ValueError:
                self.show_error_popup("Error: Invalid box size format.")
                return

        # Calcular el total basado en el subtotal y el descuento
        try:
            subtotal = float(self.subtotal_input.text.strip()) if self.subtotal_input.text.strip() else 0.0
        except ValueError:
            self.show_error_popup("Error: Subtotal debe ser un número válido.")
            return

        try:
            discount = float(self.discount_input.text.strip()) if self.discount_input.text.strip() else 0.0
        except ValueError:
            self.show_error_popup("Error: Descuento debe ser un número válido.")
            return

        # Calcular el total
        total = subtotal - discount if subtotal > 0 else 0.0
        if total < 0:
            self.show_error_popup("Error: El descuento no puede ser mayor que el subtotal.")
            return

        # Actualizar los campos de descuento y total
        self.discount_input.text = f"{discount:.2f}"
        self.total_input.text = f"{total:.2f}"

        # Recopilar datos
        data = {
            'shipper': self.shipper_input.text.strip(),
            'address': self.address_input.text.strip(),
            'phone': self.phone_input.text.strip(),
            'shippee': self.shippee_input.text.strip(),
            'destination': self.destination_input.text.strip(),
            'recipient_id': self.recipient_id_input.text.strip(),
            'recipient_phone': self.recipient_phone_input.text.strip(),
            'weight': self.weight_input.text.strip(),
            'length': length,
            'width': width,
            'height': height,
            'subtotal': subtotal,
            'discount': discount,
            'total': total,
            'cash': self.cash_input.text.strip(),
            'card': self.card_input.text.strip(),
            'shipping_code': self.shipping_code_input.text.strip(),
            'date': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        connection = sqlite3.connect(self.db_path)
        cursor = connection.cursor()

        try:
            if self.is_edit_mode:
                # Update the existing record, including recipient_id
                cursor.execute("""
                    UPDATE recibos
                    SET shipper = :shipper, address = :address, phone = :phone, shippee = :shippee,
                        destination = :destination, recipient_id = :recipient_id, recipient_phone = :recipient_phone,
                        weight = :weight, length = :length, width = :width, height = :height,
                        subtotal = :subtotal, discount = :discount, total = :total, cash = :cash,
                        card = :card, shipping_code = :shipping_code, date = :date
                    WHERE phone = :original_phone
                """, {**data, 'original_phone': self.editing_sender_phone})
                print(f"Recibo con phone '{self.phone_input.text.strip()}' actualizado exitosamente.")
            else:
                # Insert a new record
                cursor.execute("""
                    INSERT INTO recibos (
                        shipper, address, phone, shippee, destination, recipient_id, recipient_phone,
                        weight, length, width, height, subtotal,
                        discount, total, cash, card, shipping_code, date
                    ) VALUES (
                        :shipper, :address, :phone, :shippee, :destination, :recipient_id, :recipient_phone,
                        :weight, :length, :width, :height, :subtotal,
                        :discount, :total, :cash, :card, :shipping_code, :date
                    )
                """, data)
                print("Recibo guardado exitosamente.")

            connection.commit()
        except sqlite3.IntegrityError:
            self.show_error_popup(f"Error: Ya existe un recibo con el número de teléfono '{data['phone']}'.")
            return
        finally:
            connection.close()

        # Generar y abrir el recibo
        self.generate_receipt_image(data)

        # Limpiar los campos después de guardar
        self.clear_text_inputs()

        # Reset edit mode
        self.is_edit_mode = False
        self.editing_sender_phone = None

    def generate_receipt_image(self, data):
        """Generate a receipt image using the provided data."""
        # Create the receipt image
        image = Image.new("RGB", (1200, 1600), color="white")
        draw = ImageDraw.Draw(image)

        # Load fonts
        try:
            font_path = os.path.join("C:\\Windows\\Fonts", "arialbd.ttf")  # Use Arial Bold for the title
            title_font = ImageFont.truetype(font_path, 28)  # Font for the title (bold and larger)
            small_font = ImageFont.truetype(font_path.replace("arialbd.ttf", "arial.ttf"), 18)  # Smaller font for details
        except IOError:
            print("Warning: Arial font not found. Using default font.")
            title_font = ImageFont.load_default()
            small_font = ImageFont.load_default()

        # Define a vertical offset to move everything down
        vertical_offset = 50  # Adjust this value to move content further down

        # Draw header (centered and bold)
        title_text = "Lista de Empaque (Packing List)"
        title_bbox = title_font.getbbox(title_text)  # Get the bounding box of the title text
        title_width = title_bbox[2] - title_bbox[0]  # Calculate the width of the text
        title_x = (1200 - title_width) // 2  # Center the title horizontally
        draw.text((title_x, 20 + vertical_offset), title_text, fill="black", font=title_font)

        # Draw sender and recipient information
        draw.rectangle((20, 60 + vertical_offset, 580, 300 + vertical_offset), outline="black", width=2)
        draw.text((30, 70 + vertical_offset), f"Remitente (Shipper):\n{data['shipper']}\n{data['address']}\n{data['phone']}", fill="black", font=small_font)

        draw.rectangle((600, 60 + vertical_offset, 1180, 300 + vertical_offset), outline="black", width=2)

        # Wrap the destination text to fit within the box
        destination_text = data['destination']
        wrapped_destination = textwrap.fill(destination_text, width=50)  # Adjust width as needed

        # Combine the recipient information with the wrapped destination text
        recipient_text = f"Destinatario (Shippee):\n{data['shippee']}\n{wrapped_destination}\nPhone: {data.get('recipient_phone', 'N/A')}"

        # Draw the recipient text
        draw.text((610, 70 + vertical_offset), recipient_text, fill="black", font=small_font)

        # Draw shipping details
        draw.rectangle((20, 320 + vertical_offset, 1180, 400 + vertical_offset), outline="black", width=2)
        draw.text((30, 330 + vertical_offset), f"Oficina (Office): Charlotte, NC", fill="black", font=small_font)

        # Add the new text below the office information
        draw.text((30, 360 + vertical_offset), "Para rastreo llamar al (980)-214-5130", fill="black", font=small_font)

        # Continue with the rest of the receipt generation...
        draw.text((400, 330 + vertical_offset), f"Fecha (Date): {datetime.now().strftime('%Y-%m-%d')}", fill="black", font=small_font)
        draw.text((800, 330 + vertical_offset), f"Código de Envío: {data['shipping_code']}", fill="black", font=small_font)

        # Draw weight and dimensions
        draw.rectangle((20, 420 + vertical_offset, 1180, 500 + vertical_offset), outline="black", width=2)
        draw.text((30, 430 + vertical_offset), f"Peso: {data['weight']} kg", fill="black", font=small_font)
        draw.text((400, 430 + vertical_offset), f"Largo: {data['length']} cm", fill="black", font=small_font)
        draw.text((600, 430 + vertical_offset), f"Ancho: {data['width']} cm", fill="black", font=small_font)
        draw.text((800, 430 + vertical_offset), f"Alto: {data['height']} cm", fill="black", font=small_font)

        # Draw totals
        draw.rectangle((20, 520 + vertical_offset, 1180, 600 + vertical_offset), outline="black", width=2)
        draw.text((30, 530 + vertical_offset), f"Sub-Total: ${data['subtotal']}", fill="black", font=small_font)
        draw.text((400, 530 + vertical_offset), f"Discount: ${data['discount']}", fill="black", font=small_font)
        draw.text((800, 530 + vertical_offset), f"Total: ${data['total']}", fill="black", font=small_font)

        # Draw payment details
        draw.rectangle((20, 620 + vertical_offset, 1180, 700 + vertical_offset), outline="black", width=2)
        draw.text((30, 630 + vertical_offset), f"Cash: ${data['cash']}", fill="black", font=small_font)
        draw.text((400, 630 + vertical_offset), f"Card: ${data['card']}", fill="black", font=small_font)

        # Draw item description table
        draw.rectangle((20, 720 + vertical_offset, 1180, 1000 + vertical_offset), outline="black", width=2)
        draw.text((30, 730 + vertical_offset), "Cantidad (Quantity)", fill="black", font=small_font)
        draw.text((400, 730 + vertical_offset), "Descripción de Artículo (Article Description)", fill="black", font=small_font)
        draw.text((1000, 730 + vertical_offset), "Valor (Worth)", fill="black", font=small_font)

        # Draw footer
        footer_y = 1450 + vertical_offset  # Posición vertical del pie de página (más abajo)
        line_y = footer_y - 10  # Línea horizontal justo encima del texto

        # Dibujar líneas horizontales
        draw.line((20, line_y, 380, line_y), fill="black", width=1)  # Línea para la primera columna
        draw.line((400, line_y, 760, line_y), fill="black", width=1)  # Línea para la segunda columna
        draw.line((780, line_y, 1180, line_y), fill="black", width=1)  # Línea para la tercera columna

        # Dibujar el texto del pie de página
        draw.text((30, footer_y), "All the above information is correct.\nTodo la información arriba es correcta.", fill="black", font=small_font)
        draw.text((400, footer_y), "I agree with the terms and conditions.\nEstoy de acuerdo con los términos y condiciones.", fill="black", font=small_font)
        draw.text((800, footer_y), "I don't need supplementary insurance.\nNo necesito seguro adicional.", fill="black", font=small_font)

        # Guardar la imagen con el número de teléfono del remitente (sender)
        sender_phone = data.get('phone', 'unknown').replace("+", "").strip()
        if not sender_phone:
            sender_phone = "unknown"
        image_path = os.path.join(os.getcwd(), f"{sender_phone}.png")
        try:
            image.save(image_path)
            print(f"Receipt image saved successfully at: {image_path}")
        except Exception as e:
            self.show_error_popup(f"Error saving receipt image: {e}")
            return

        # Open the image in the Windows photo viewer
        try:
            os.startfile(image_path)
        except Exception as e:
            self.show_error_popup(f"Error opening receipt image: {e}")

    def generate_receipt_from_data(self, data):
        """Generate a receipt using the provided data and open it."""
        # Create the receipt image
        image = Image.new("RGB", (1200, 1600), color="white")
        draw = ImageDraw.Draw(image)

        # Load a larger font
        try:
            font_path = os.path.join("C:\\Windows\\Fonts", "arial.ttf")  # Typical path on Windows
            font = ImageFont.truetype(font_path, 24)  # Use Arial with size 24
        except IOError:
            print("Warning: Arial font not found. Using default font.")
            font = ImageFont.load_default()  # Use default font if Arial is unavailable

        # Draw header
        draw.text((20, 20), "Packing List", fill="black", font=font)

        # Draw sender and recipient information
        draw.rectangle((20, 60, 580, 300), outline="black", width=2)
        draw.text((30, 70), f"Sender (Shipper):\n{data['shipper']}\n{data['address']}\n{data['phone']}", fill="black", font=font)

        # Draw recipient information
        draw.rectangle((600, 60, 1180, 300), outline="black", width=2)
        draw.text(
            (610, 70),  # Adjust starting position for recipient details
            f"Recipient (Shippee):\n"
            f"{data['shippee']}\n"
            f"{data['destination']}\n"
            f"ID: {data.get('recipient_phone', 'N/A')}\n"
            f"Phone: {data.get('recipient_phone', 'N/A')}",
            fill="black",
            font=font
        )

        # Draw shipping details
        draw.rectangle((20, 320, 1180, 400), outline="black", width=2)
        draw.text((30, 330), f"Office: Charlotte, NC", fill="black", font=font)

        # Add date and time
        current_date = datetime.now().strftime('%Y-%m-%d')
        current_time = datetime.now().strftime('%H:%M:%S')  # Format for the time
        draw.text((400, 330), f"Date: {current_date}", fill="black", font=font)
        draw.text((400, 360), f"Time: {current_time}", fill="black", font=font)  # Add time below the date

        draw.text((800, 330), f"Shipping Code: {data['shipping_code']}", fill="black", font=font)

        # Draw weight and dimensions
        draw.rectangle((20, 420, 1180, 500), outline="black", width=2)
        draw.text((30, 430), f"Weight: {data['weight']} kg", fill="black", font=font)
        draw.text((400, 430), f"Length: {data['length']} cm", fill="black", font=font)
        draw.text((600, 430), f"Width: {data['width']} cm", fill="black", font=font)
        draw.text((800, 430), f"Height: {data['height']} cm", fill="black", font=font)

        # Draw totals
        draw.rectangle((20, 520, 1180, 600), outline="black", width=2)
        draw.text((30, 530), f"Sub-Total: {data['subtotal']}", fill="black", font=font)
        draw.text((400, 530), f"Discount: {data['discount']}", fill="black", font=font)
        draw.text((800, 530), f"Total: {data['total']}", fill="black", font=font)

        # Draw payment details
        draw.rectangle((20, 620, 1180, 700), outline="black", width=2)
        draw.text((30, 630), f"Cash: {data['cash']}", fill="black", font=font)
        draw.text((400, 630), f"Card: {data['card']}", fill="black", font=font)

        # Save the image with the recipient's ID (without "ID" prefix)
        recipient_phone = data.get('recipient_phone', 'unknown').replace("+", "").strip()
        image_path = os.path.join(os.getcwd(), f"{recipient_phone}.png")
        try:
            image.save(image_path)
        except Exception as e:
            self.show_error_popup(f"Error saving receipt: {e}")
            return

        # Open the image in the Windows photo viewer
        try:
            os.startfile(image_path)
        except Exception as e:
            self.show_error_popup(f"Error opening receipt: {e}")

    def show_open_popup(self, instance):
        """Show a popup to enter the sender's phone number to open the receipt."""
        popup_layout = BoxLayout(orientation='vertical', spacing=10, padding=10)
        popup_layout.add_widget(Label(text="Enter the sender's phone number to open the receipt:", size_hint=(1, 0.2)))
        self.popup_phone_input = TextInput(hint_text="Sender's Phone Number", multiline=False)
        popup_layout.add_widget(self.popup_phone_input)

        open_button = Button(text="Open", size_hint=(1, 0.2))
        open_button.bind(on_press=self.open_receipt)
        popup_layout.add_widget(open_button)

        self.open_popup = Popup(title="Open Receipt",
                                content=popup_layout,
                                size_hint=(0.8, 0.5))
        self.open_popup.open()

    def open_receipt(self, instance):
        """Search for receipts by sender's phone number and let the user select which one to load."""
        sender_phone = self.popup_phone_input.text.strip()
        if not sender_phone:
            self.show_error_popup("Error: The sender's phone number is required to open a receipt.")
            return

        connection = sqlite3.connect(self.db_path)
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM recibos WHERE phone = ?", (sender_phone,))
        rows = cursor.fetchall()
        connection.close()

        if not rows:
            self.show_error_popup(f"Error: No receipt found with sender's phone number '{sender_phone}'.")
            return

        columns = [
            'id', 'shipper', 'address', 'phone', 'shippee', 'destination',
            'recipient_id', 'recipient_phone', 'weight', 'length', 'width',
            'height', 'subtotal', 'discount', 'total', 'cash', 'card',
            'shipping_code', 'date'
        ]

        if len(rows) == 1:
            data = dict(zip(columns, rows[0]))
            self.load_receipt_fields(data)
            self.open_popup.dismiss()
        else:
            # Show a popup to select which receipt to load
            popup_layout = BoxLayout(orientation='vertical', spacing=10, padding=10)
            popup_layout.add_widget(Label(text="Select a receipt by date:", size_hint=(1, 0.2)))
            from kivy.uix.spinner import Spinner
            date_options = [row[columns.index('date')] for row in rows]
            # Set the first date as default
            self.receipt_select_spinner = Spinner(text=date_options[0], values=date_options, size_hint=(1, 0.2))
            popup_layout.add_widget(self.receipt_select_spinner)

            select_button = Button(text="Load", size_hint=(1, 0.2))
            def load_selected_receipt(instance):
                selected_date = self.receipt_select_spinner.text
                for row in rows:
                    if row[columns.index('date')] == selected_date:
                        data = dict(zip(columns, row))
                        self.load_receipt_fields(data)
                        break
                self.select_receipt_popup.dismiss()
                self.open_popup.dismiss()
            select_button.bind(on_press=load_selected_receipt)
            popup_layout.add_widget(select_button)

            self.select_receipt_popup = Popup(title="Select Receipt", content=popup_layout, size_hint=(0.8, 0.5))
            self.select_receipt_popup.open()

    def load_receipt_fields(self, data):
        """Populate the fields with the data from a receipt dictionary."""
        self.shipper_input.text = data.get("shipper", "")
        self.address_input.text = data.get("address", "")
        self.phone_input.text = data.get("phone", "")
        self.shippee_input.text = data.get("shippee", "")
        self.destination_input.text = data.get("destination", "")
        self.recipient_id_input.text = data.get("recipient_id", "")
        self.recipient_phone_input.text = data.get("recipient_phone", "")
        self.weight_input.text = str(data.get("weight", ""))
        self.subtotal_input.text = str(data.get("subtotal", ""))
        self.discount_input.text = str(data.get("discount", ""))
        self.total_input.text = str(data.get("total", ""))
        self.cash_input.text = str(data.get("cash", ""))
        self.card_input.text = str(data.get("card", ""))
        self.shipping_code_input.text = data.get("shipping_code", "")

        # Set the box size in the spinner
        length = data.get("length", 0)
        width = data.get("width", 0)
        height = data.get("height", 0)
        box_size = f"{int(length)}x{int(width)}x{int(height)}"
        if hasattr(self, 'box_size_spinner') and box_size in self.box_size_spinner.values:
            self.box_size_spinner.text = box_size
        else:
            self.box_size_spinner.text = "Irregular"

        # Al abrir, NO activar modo edición
        self.is_edit_mode = False
        self.editing_sender_phone = None

        print(f"Data for sender phone '{data.get('phone', '').strip()}' loaded successfully.")
        self.open_popup.dismiss()

    def generate_receipt_from_data(self, data):
        """Generate a receipt using the provided data and open it."""
        # Create the receipt image
        image = Image.new("RGB", (1200, 1600), color="white")
        draw = ImageDraw.Draw(image)

        # Load a larger font
        try:
            font_path = os.path.join("C:\\Windows\\Fonts", "arial.ttf")  # Typical path on Windows
            font = ImageFont.truetype(font_path, 24)  # Use Arial with size 24
        except IOError:
            print("Warning: Arial font not found. Using default font.")
            font = ImageFont.load_default()  # Use default font if Arial is unavailable

        # Draw header
        draw.text((20, 20), "Packing List", fill="black", font=font)

        # Draw sender and recipient information
        draw.rectangle((20, 60, 580, 300), outline="black", width=2)
        draw.text((30, 70), f"Sender (Shipper):\n{data['shipper']}\n{data['address']}\n{data['phone']}", fill="black", font=font)

        # Draw recipient information
        draw.rectangle((600, 60, 1180, 300), outline="black", width=2)
        draw.text(
            (610, 70),  # Adjust starting position for recipient details
            f"Recipient (Shippee):\n"
            f"{data['shippee']}\n"
            f"{data['destination']}\n"
            f"ID: {data.get('recipient_phone', 'N/A')}\n"
            f"Phone: {data.get('recipient_phone', 'N/A')}",
            fill="black",
            font=font
        )

        # Draw shipping details
        draw.rectangle((20, 320, 1180, 400), outline="black", width=2)
        draw.text((30, 330), f"Office: Charlotte, NC", fill="black", font=font)

        # Add date and time
        current_date = datetime.now().strftime('%Y-%m-%d')
        current_time = datetime.now().strftime('%H:%M:%S')  # Format for the time
        draw.text((400, 330), f"Date: {current_date}", fill="black", font=font)
        draw.text((400, 360), f"Time: {current_time}", fill="black", font=font)  # Add time below the date

        draw.text((800, 330), f"Shipping Code: {data['shipping_code']}", fill="black", font=font)

        # Draw weight and dimensions
        draw.rectangle((20, 420, 1180, 500), outline="black", width=2)
        draw.text((30, 430), f"Weight: {data['weight']} kg", fill="black", font=font)
        draw.text((400, 430), f"Length: {data['length']} cm", fill="black", font=font)
        draw.text((600, 430), f"Width: {data['width']} cm", fill="black", font=font)
        draw.text((800, 430), f"Height: {data['height']} cm", fill="black", font=font)

        # Draw totals
        draw.rectangle((20, 520, 1180, 600), outline="black", width=2)
        draw.text((30, 530), f"Sub-Total: {data['subtotal']}", fill="black", font=font)
        draw.text((400, 530), f"Discount: {data['discount']}", fill="black", font=font)
        draw.text((800, 530), f"Total: {data['total']}", fill="black", font=font)

        # Draw payment details
        draw.rectangle((20, 620, 1180, 700), outline="black", width=2)
        draw.text((30, 630), f"Cash: {data['cash']}", fill="black", font=font)
        draw.text((400, 630), f"Card: {data['card']}", fill="black", font=font)

        # Save the image with the recipient's ID (without "ID" prefix)
        recipient_phone = data.get('recipient_phone', 'unknown').replace("+", "").strip()
        image_path = os.path.join(os.getcwd(), f"{recipient_phone}.png")
        try:
            image.save(image_path)
        except Exception as e:
            self.show_error_popup(f"Error saving receipt: {e}")
            return

        # Open the image in the Windows photo viewer
        try:
            os.startfile(image_path)
        except Exception as e:
            self.show_error_popup(f"Error opening receipt: {e}")

    def show_edit_popup(self, instance):
        """Show a popup to enter the sender's phone number to edit."""
        popup_layout = BoxLayout(orientation='vertical', spacing=10, padding=10)
        popup_layout.add_widget(Label(text="Enter the sender's phone number to edit:", size_hint=(1, 0.2)))
        self.popup_edit_input = TextInput(hint_text="Sender's Phone Number", multiline=False)
        popup_layout.add_widget(self.popup_edit_input)

        load_button = Button(text="Load", size_hint=(1, 0.2))
        load_button.bind(on_press=self.load_receipt_data)
        popup_layout.add_widget(load_button)

        self.edit_popup = Popup(title="Edit Receipt",
                                content=popup_layout,
                                size_hint=(0.8, 0.5))
        self.edit_popup.open()

    def load_receipt_data(self, instance):
        """Load receipt data from the database using the sender's phone number."""
        sender_phone = self.popup_edit_input.text.strip()
        if not sender_phone:
            self.show_error_popup("Error: The sender's phone number is required to edit a receipt.")
            return

        connection = sqlite3.connect(self.db_path)
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM recibos WHERE phone = ?", (sender_phone,))
        rows = cursor.fetchall()
        connection.close()

        columns = [
            'id', 'shipper', 'address', 'phone', 'shippee', 'destination',
            'recipient_id', 'recipient_phone', 'weight', 'length', 'width',
            'height', 'subtotal', 'discount', 'total', 'cash', 'card',
            'shipping_code', 'date'
        ]

        if not rows:
            self.show_error_popup(f"Error: No receipt found with sender's phone number '{sender_phone}'.")
            return

        if len(rows) == 1:
            data = dict(zip(columns, rows[0]))
            self.shipper_input.text = data.get("shipper", "")
            self.address_input.text = data.get("address", "")
            self.phone_input.text = data.get("phone", "")
            self.shippee_input.text = data.get("shippee", "")
            self.destination_input.text = data.get("destination", "")
            self.recipient_id_input.text = data.get("recipient_id", "")
            self.recipient_phone_input.text = data.get("recipient_phone", "")
            self.weight_input.text = str(data.get("weight", ""))
            self.subtotal_input.text = str(data.get("subtotal", ""))
            self.discount_input.text = str(data.get("discount", ""))
            self.total_input.text = str(data.get("total", ""))
            self.cash_input.text = str(data.get("cash", ""))
            self.card_input.text = str(data.get("card", ""))
            self.shipping_code_input.text = data.get("shipping_code", "")

            # Set the box size in the spinner
            length = data.get("length", 0)
            width = data.get("width", 0)
            height = data.get("height", 0)
            box_size = f"{int(length)}x{int(width)}x{int(height)}"
            if box_size in self.box_size_spinner.values:
                self.box_size_spinner.text = box_size
            else:
                self.box_size_spinner.text = "Irregular"  # Default to "Irregular" if size is not in the list

            # Activate edit mode
            self.is_edit_mode = True
            self.editing_sender_phone = sender_phone

            print(f"Data for sender phone '{sender_phone}' loaded successfully.")
            self.edit_popup.dismiss()
        else:
            # Show a popup to select which receipt to edit
            popup_layout = BoxLayout(orientation='vertical', spacing=10, padding=10)
            popup_layout.add_widget(Label(text="Select a receipt by date:", size_hint=(1, 0.2)))
            from kivy.uix.spinner import Spinner
            date_options = [row[columns.index('date')] for row in rows]
            self.edit_receipt_select_spinner = Spinner(text="Select Date", values=date_options, size_hint=(1, 0.2))
            popup_layout.add_widget(self.edit_receipt_select_spinner)

            select_button = Button(text="Load", size_hint=(1, 0.2))
            def load_selected_edit_receipt(instance):
                selected_date = self.edit_receipt_select_spinner.text
                for row in rows:
                    if row[columns.index('date')] == selected_date:
                        data = dict(zip(columns, row))
                        self.shipper_input.text = data.get("shipper", "")
                        self.address_input.text = data.get("address", "")
                        self.phone_input.text = data.get("phone", "")
                        self.shippee_input.text = data.get("shippee", "")
                        self.destination_input.text = data.get("destination", "")
                        self.recipient_id_input.text = data.get("recipient_id", "")
                        self.recipient_phone_input.text = data.get("recipient_phone", "")
                        self.weight_input.text = str(data.get("weight", ""))
                        self.subtotal_input.text = str(data.get("subtotal", ""))
                        self.discount_input.text = str(data.get("discount", ""))
                        self.total_input.text = str(data.get("total", ""))
                        self.cash_input.text = str(data.get("cash", ""))
                        self.card_input.text = str(data.get("card", ""))
                        self.shipping_code_input.text = data.get("shipping_code", "")

                        # Set the box size in the spinner
                        length = data.get("length", 0)
                        width = data.get("width", 0)
                        height = data.get("height", 0)
                        box_size = f"{int(length)}x{int(width)}x{int(height)}"
                        if box_size in self.box_size_spinner.values:
                            self.box_size_spinner.text = box_size
                        else:
                            self.box_size_spinner.text = "Irregular"

                        # Activate edit mode
                        self.is_edit_mode = True
                        self.editing_sender_phone = data.get("phone", "").strip()
                        break
                self.select_edit_receipt_popup.dismiss()  # Cierra el popup de selección
                self.edit_popup.dismiss()  # Cierra el popup principal
            select_button.bind(on_press=load_selected_edit_receipt)
            popup_layout.add_widget(select_button)

            self.select_edit_receipt_popup = Popup(title="Select Receipt to Edit", content=popup_layout, size_hint=(0.8, 0.5))
            self.select_edit_receipt_popup.open()

    def save_edited_data(self, original_phone):
        """Save the edited data back to the SQLite database."""
        connection = sqlite3.connect(self.db_path)
        cursor = connection.cursor()

        try:
            cursor.execute("""
                UPDATE recibos
                SET shipper = ?, address = ?, phone = ?, shippee = ?, destination = ?,
                    recipient_phone = ?, recipient_phone = ?, weight = ?, length = ?, width = ?,
                    height = ?, subtotal = ?, discount = ?, total = ?, cash = ?, card = ?,
                    shipping_code = ?
                WHERE recipient_phone = ?
            """, (
                self.shipper_input.text.strip(),
                self.address_input.text.strip(),
                self.phone_input.text.strip(),
                self.shippee_input.text.strip(),
                self.destination_input.text.strip(),
                self.recipient_phone_input.text.strip(),
                self.recipient_phone_input.text.strip(),
                self.weight_input.text.strip(),
                0,  # Puedes agregar un campo para la longitud si es necesario
                0,
                0,
                self.subtotal_input.text.strip(),
                self.discount_input.text.strip(),
                self.total_input.text.strip(),
                self.cash_input.text.strip(),
                self.card_input.text.strip(),
                self.shipping_code_input.text.strip(),
                original_phone
            ))
            connection.commit()

            if cursor.rowcount > 0:
                print(f"Datos del número de teléfono '{original_phone}' actualizados exitosamente.")
            else:
                self.show_error_popup(f"Error: No se encontró el número de teléfono '{original_phone}' en la base de datos.")
        except Exception as e:
            self.show_error_popup(f"Error al actualizar los datos: {e}")
        finally:
            connection.close()

        # Limpiar los campos después de editar
        self.clear_text_inputs()

    def send_receipt_via_whatsapp(self, instance):
        """Send the selected receipt via WhatsApp."""
        recipient_number = self.whatsapp_number_input.text.strip()
        if not recipient_number:
            self.show_error_popup("Error: Recipient's WhatsApp number is required.")
            return

        recipient_phone = self.selected_file_input.text.strip().replace("+", "").strip()
        if not recipient_phone:
            self.show_error_popup("Error: Recipient Phone number is required.")
            return

        # Path to the receipt PNG
        image_path = os.path.join(os.getcwd(), f"{recipient_phone}.png")
        if not os.path.exists(image_path):
            self.show_error_popup(f"Error: Receipt file '{image_path}' does not exist.")
            return

        try:
            # Send the image via WhatsApp
            print(f"Sending receipt '{recipient_phone}.png' to {recipient_number} via WhatsApp...")
            kit.sendwhats_image(
                receiver=recipient_number,
                img_path=image_path,
                caption=f"Hello, here is your receipt: {recipient_phone}."
            )
            print("Receipt sent successfully!")
        except Exception as e:
            self.show_error_popup(f"Error sending receipt via WhatsApp: {e}")

    def show_whatsapp_popup(self, instance):
        """Show a popup to enter the WhatsApp number and select the receipt file."""
        popup_layout = BoxLayout(orientation='vertical', spacing=10, padding=10)

        # Input for WhatsApp number
        popup_layout.add_widget(Label(text="Enter the recipient's WhatsApp number:", size_hint=(1, 0.2)))
        self.whatsapp_number_input = TextInput(hint_text="e.g., +1234567890", multiline=False)
        popup_layout.add_widget(self.whatsapp_number_input)

        # Input for selecting the receipt file
        popup_layout.add_widget(Label(text="Enter the receipt file name (without .png):", size_hint=(1, 0.2)))
        self.selected_file_input = TextInput(hint_text="e.g., receipt_name", multiline=False)
        popup_layout.add_widget(self.selected_file_input)

        # Send button
        send_button = Button(text="Send", size_hint=(1, 0.2))
        send_button.bind(on_press=self.send_receipt_via_whatsapp)
        popup_layout.add_widget(send_button)

        self.whatsapp_popup = Popup(title="Send Receipt via WhatsApp",
                                    content=popup_layout,
                                    size_hint=(0.8, 0.5))
        self.whatsapp_popup.open()

    def show_error_popup(self, error_message):
        """Show a popup with an error message."""
        popup_layout = BoxLayout(orientation='vertical', spacing=10, padding=10)
        popup_layout.add_widget(Label(text=error_message, size_hint=(1, 0.8)))
        close_button = Button(text="Close", size_hint=(1, 0.2))
        close_button.bind(on_press=lambda instance: self.error_popup.dismiss())
        popup_layout.add_widget(close_button)

        self.error_popup = Popup(title="Error", content=popup_layout, size_hint=(0.8, 0.4))
        self.error_popup.open()

    def show_delete_popup(self, instance):
        """Show a popup to enter the sender's phone number to delete."""
        popup_layout = BoxLayout(orientation='vertical', spacing=10, padding=10)
        popup_layout.add_widget(Label(text="Enter the sender's phone number to delete:", size_hint=(1, 0.2)))
        self.delete_input = TextInput(hint_text="Sender's Phone Number", multiline=False)
        popup_layout.add_widget(self.delete_input)

        delete_button = Button(text="Delete", size_hint=(1, 0.2))
        delete_button.bind(on_press=self.delete_person)
        popup_layout.add_widget(delete_button)

        self.delete_popup = Popup(title="Delete Recipient",
                                  content=popup_layout,
                                  size_hint=(0.8, 0.5))
        self.delete_popup.open()

    def delete_person(self, instance):
        """Delete a person from the database by sender's phone number."""
        sender_phone = self.delete_input.text.strip()
        if not sender_phone:
            self.show_error_popup("Error: Sender's phone number is required to delete.")
            return

        connection = sqlite3.connect(self.db_path)
        cursor = connection.cursor()
        cursor.execute("DELETE FROM recibos WHERE phone = ?", (sender_phone,))
        connection.commit()
        connection.close()

        if cursor.rowcount > 0:
            print(f"Recipient with sender phone '{sender_phone}' deleted successfully.")
            self.delete_popup.dismiss()
        else:
            self.show_error_popup(f"Error: Sender phone '{sender_phone}' not found in the database.")

        self.clear_text_inputs()

    def show_monthly_report(self, instance):
        """Generate and display a monthly report with sender, recipient details, box size, and total."""
        connection = sqlite3.connect(self.db_path)
        cursor = connection.cursor()

        # Get the current month and year
        current_month = datetime.now().strftime("%Y-%m")
        cursor.execute("""
            SELECT shipper, phone, shippee, recipient_phone, length, width, height, total FROM recibos
            WHERE date LIKE ?
        """, (f"{current_month}%",))
        report_details = cursor.fetchall()
        connection.close()

        # Display the report (existing functionality)
        self.display_monthly_report_popup(report_details, current_month)

    def display_monthly_report_popup(self, report_details, current_month):
        """Display a popup with the monthly report showing sender, recipient details, box size, and total."""
        # Create the popup layout
        popup_layout = BoxLayout(orientation="vertical", spacing=10, padding=10)

        # Add a title
        title_label = Label(
            text=f"Monthly Report ({current_month})",
            font_size=20,
            size_hint=(1, None),
            height=40
        )
        popup_layout.add_widget(title_label)

        # Create a grid layout for the details
        grid = GridLayout(cols=6, spacing=5, size_hint=(1, None))
        grid.bind(minimum_height=grid.setter('height'))

        # Add headers
        grid.add_widget(Label(text="Sender Name", font_size=16, size_hint_y=None, height=40))
        grid.add_widget(Label(text="Sender Phone", font_size=16, size_hint_y=None, height=40))
        grid.add_widget(Label(text="Recipient Name", font_size=16, size_hint_y=None, height=40))
        grid.add_widget(Label(text="Recipient Phone", font_size=16, size_hint_y=None, height=40))
        grid.add_widget(Label(text="Box Size", font_size=16, size_hint_y=None, height=40))
        grid.add_widget(Label(text="Total", font_size=16, size_hint_y=None, height=40))

        # Add rows for each record
        for record in report_details:
            shipper, phone, shippee, recipient_phone, length, width, height, total = record
            box_size = f"{int(length)}x{int(width)}x{int(height)}" if length and width and height else "Irregular"
            grid.add_widget(Label(text=shipper, font_size=14, size_hint_y=None, height=30))  # Sender Name
            grid.add_widget(Label(text=phone, font_size=14, size_hint_y=None, height=30))  # Sender Phone
            grid.add_widget(Label(text=shippee, font_size=14, size_hint_y=None, height=30))  # Recipient Name
            grid.add_widget(Label(text=recipient_phone, font_size=14, size_hint_y=None, height=30))  # Recipient Phone
            grid.add_widget(Label(text=box_size, font_size=14, size_hint_y=None, height=30))  # Box Size
            grid.add_widget(Label(text=f"${total:.2f}", font_size=14, size_hint_y=None, height=30))  # Total

        # Add the grid to a scroll view
        scroll_view = ScrollView(size_hint=(1, None), size=(Window.width * 0.8, 300))
        scroll_view.add_widget(grid)
        popup_layout.add_widget(scroll_view)

        # Add a button to export to Excel
        export_button = Button(text="Export to Excel", size_hint=(1, None), height=50)
        export_button.bind(on_press=lambda x: self.create_monthly_excel(report_details, current_month))
        popup_layout.add_widget(export_button)

        # Add a close button
        close_button = Button(text="Close", size_hint=(1, None), height=50)
        close_button.bind(on_press=lambda x: popup.dismiss())
        popup_layout.add_widget(close_button)

        # Create and open the popup
        popup = Popup(title="Monthly Report", content=popup_layout, size_hint=(0.9, 0.9))
        popup.open()

    def create_box_size_spinner(self):
        """Create a Spinner for selecting box sizes with scroll functionality."""
        box_sizes = [
            "12x12x12", "14x14x14", "16x16x16", "18x18x18", "20x20x20",
            "22x22x22", "24x24x24", "28x28x28", "28x18x18", "28x20x20",
            "40x20x20", "Irregular", "48x40x65", "48x40x80"
        ]

        # Create a custom dropdown with scroll functionality
        class ScrollableDropDown(DropDown):
            def __init__(self, **kwargs):
                super().__init__(**kwargs)
                self.auto_dismiss = True  # Close dropdown when an option is selected
                self.container.spacing = 5  # Add spacing between options
                self.container.size_hint_y = None
                self.container.bind(minimum_height=self.container.setter('height'))

        # Create the spinner and attach the custom dropdown class
        spinner = Spinner(
            text="Select Box Size",  # Default text
            size_hint=(1, None),
            height=40,
            font_size=16,
            dropdown_cls=ScrollableDropDown  # Pass the class, not an instance
        )

        # Add options to the spinner
        for size in box_sizes:
            spinner.values.append(size)

        spinner.bind(text=self.on_box_size_selected)  # Optional: Handle selection
        self.box_size_spinner = spinner  # Save the spinner as an attribute
        return spinner

    def on_box_size_selected(self, spinner, text):
        """Handle the selection of a box size."""
        print(f"Selected box size: {text}")

    def create_monthly_excel(self, report_details, current_month):
        """Create an Excel file with the monthly report details."""
        file_name = f"Monthly_Report_{current_month}.csv"
        file_path = os.path.join(os.getcwd(), file_name)

        try:
            # Write the data to a CSV file
            with open(file_path, mode="w", newline="", encoding="utf-8") as file:
                writer = csv.writer(file)
                # Write the headers
                writer.writerow(["Sender Name", "Sender Phone", "Recipient Name", "Recipient Phone", "Box Size", "Total"])
                # Write the rows
                for record in report_details:
                    shipper, phone, shippee, recipient_phone, length, width, height, total = record
                    box_size = f"{int(length)}x{int(width)}x{int(height)}" if length and width and height else "Irregular"
                    writer.writerow([shipper, phone, shippee, recipient_phone, box_size, f"${total:.2f}"])

            print(f"Excel file '{file_name}' created successfully at {file_path}.")
            self.show_success_popup(f"Excel file '{file_name}' created successfully.")
        except Exception as e:
            self.show_error_popup(f"Error creating Excel file: {e}")

    def show_success_popup(self, message):
        """Show a popup with a success message."""
        popup_layout = BoxLayout(orientation='vertical', spacing=10, padding=10)
        popup_layout.add_widget(Label(text=message, size_hint=(1, 0.8)))
        close_button = Button(text="Close", size_hint=(1, 0.2))
        close_button.bind(on_press=lambda instance: self.success_popup.dismiss())
        popup_layout.add_widget(close_button)

        self.success_popup = Popup(title="Success", content=popup_layout, size_hint=(0.8, 0.4))
        self.success_popup.open()

    def check_and_create_monthly_excel(self):
        """Check if 30 days have passed since the last Excel creation and create a new one if needed."""
        last_created_file = "last_excel_date.txt"
        current_date = datetime.now().date()

        # Check if the file exists
        if os.path.exists(last_created_file):
            with open(last_created_file, "r") as file:
                last_date = datetime.strptime(file.read().strip(), "%Y-%m-%d").date()
                # If 30 days have passed, create a new Excel file
                if (current_date - last_date).days >= 30:
                    self.generate_monthly_excel(current_date, last_created_file)
        else:
            # If the file doesn't exist, create the first Excel file
            self.generate_monthly_excel(current_date, last_created_file)

    def generate_monthly_excel(self, current_date, last_created_file):
        """Generate the monthly Excel file and update the last creation date."""
        connection = sqlite3.connect(self.db_path)
        cursor = connection.cursor()

        # Get all data for the current month
        current_month = current_date.strftime("%Y-%m")
        cursor.execute("""
            SELECT shipper, phone, shippee, recipient_phone, length, width, height, total FROM recibos
            WHERE date LIKE ?
        """, (f"{current_month}%",))
        report_details = cursor.fetchall()
        connection.close()

        # Create the Excel file
        self.create_monthly_excel(report_details, current_month)

        # Update the last creation date
        with open(last_created_file, "w") as file:
            file.write(current_date.strftime("%Y-%m-%d"))

if __name__ == '__main__':
    MyApp().run()
