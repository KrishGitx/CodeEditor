import main

b = main.EditorBackend()
code = '''def calculate_total(price: float, tax_rate: float = 0.05) -> float:
    """Calculates total price including tax."""
    return price * (1 + tax_rate)
'''

info = b.get_hover_info("app.py", 1, 8, code)
print("Hover info:", info)

sdk_info = b.get_hover_info("main.py", 1, 20, "ctx.notifications.show('Title', 'Msg')")
print("SDK hover info:", sdk_info)
