import streamlit as st

# This is a helper function to load Tailwind CSS from a CDN.
# The classes you were using (e.g., 'text-3xl', 'text-green-600') are from Tailwind CSS.
# Streamlit doesn't include this library by default, so you must add it for the styles to work.
def load_tailwind_css():
    """Injects a link to the Tailwind CSS stylesheet into the app's HTML head."""
    st.markdown(
        '<link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">',
        unsafe_allow_html=True
    )

def main():
    """
    A Streamlit app demonstrating the correct way to conditionally style HTML.
    """
    st.set_page_config(layout="centered", page_title="Balance Dashboard")

    # Ensure Tailwind CSS is loaded
    load_tailwind_css()

    st.title("Financial Balance Display")
    st.write(
        "This example fixes the syntax error by using Python to generate the "
        "HTML that Streamlit can render. Enter a value below to see the color change."
    )

    # Interactive widget to demonstrate the logic
    balance = st.number_input("Enter your balance:", value=5280.50, step=100.0)

    st.header("Your Current Balance")

    # --- THE FIX IS IMPLEMENTED BELOW ---

    # 1. Use a Python conditional expression ('if/else' one-liner) to determine the correct CSS class.
    #    This replaces the JavaScript ternary operator `condition ? value_if_true : value_if_false`.
    color_class = "text-green-600" if balance >= 0 else "text-red-600"

    # 2. Format the balance as a currency string.
    formatted_balance = f"${balance:,.2f}"

    # 3. Construct the complete HTML block as a Python f-string.
    #    Note that we use `class` instead of React's `className`.
    #    The original code `<p className={...}>` is JSX and is not valid in Python.
    balance_display_html = f"""
    <div style="text-align: center; padding: 2rem; border: 1px solid #e2e8f0; border-radius: 0.5rem; background-color: #f8fafc;">
      <p class="text-5xl font-bold {color_class}">
        {formatted_balance}
      </p>
      <p class="text-gray-500 mt-2">
        This style is applied dynamically with Python.
      </p>
    </div>
    """

    # 4. Render the HTML string using st.markdown.
    #    The `unsafe_allow_html=True` argument is essential for rendering HTML.
    st.markdown(balance_display_html, unsafe_allow_html=True)


if __name__ == "__main__":
    main()

