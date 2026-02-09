import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.animation import FuncAnimation
import numpy as np
from mpl_toolkits.mplot3d import Axes3D
import itertools
import re
import threading
import time
import math


class LogicalExpression:
    """Class to handle logical expression parsing and evaluation"""

    def __init__(self, expression):
        self.expression = expression.replace(' ', '')
        self.variables = self.extract_variables()
        self.parsed_expr = self.parse_expression()

    def extract_variables(self):
        """Extract unique variables from expression"""
        # Find all single letters that aren't operators
        vars_found = re.findall(r'[A-Za-z]', self.expression)
        # Remove logical operators
        operators = {'A', 'N', 'D', 'O', 'R', 'I', 'F', 'T', 'U', 'E'}
        variables = set(var for var in vars_found if var not in operators)
        return sorted(list(variables))

    def parse_expression(self):
        """Convert infix to postfix notation for easier evaluation"""
        # Replace operators with symbols for easier parsing
        expr = self.expression.upper()
        expr = expr.replace('AND', '&')
        expr = expr.replace('OR', '|')
        expr = expr.replace('NOT', '~')
        expr = expr.replace('IMPLIES', '>')
        expr = expr.replace('IFF', '=')
        expr = expr.replace('->', '>')
        expr = expr.replace('<->', '=')
        expr = expr.replace('!', '~')
        expr = expr.replace('∧', '&')
        expr = expr.replace('∨', '|')
        expr = expr.replace('¬', '~')
        expr = expr.replace('→', '>')
        expr = expr.replace('↔', '=')

        return expr

    def evaluate(self, variable_values):
        """Evaluate expression given variable values"""
        expr = self.parsed_expr

        # Replace variables with their values
        for var in self.variables:
            expr = expr.replace(var, str(int(variable_values[var])))

        # Replace logical operators with Python equivalents
        expr = expr.replace('&', ' and ')
        expr = expr.replace('|', ' or ')
        expr = expr.replace('~', ' not ')
        expr = expr.replace('>', ' <= ')  # A -> B is equivalent to not A or B
        expr = expr.replace('=', ' == ')  # A <-> B is A == B

        # Handle implications properly
        expr = re.sub(r'(\d+)\s*<=\s*(\d+)', r'(not \1 or \2)', expr)

        try:
            # Convert 0/1 to boolean for evaluation
            expr = expr.replace('1', 'True').replace('0', 'False')
            result = eval(expr)
            return int(result)
        except:
            return 0


class EnhancedTreeview(ttk.Treeview):
    """Enhanced Treeview with animation capabilities"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.highlighted_items = []

    def highlight_row(self, item, color="#4CAF50"):
        """Highlight a specific row"""
        self.tag_configure('highlight', background=color, foreground='white')
        self.item(item, tags=('highlight',))
        self.highlighted_items.append(item)

    def clear_highlights(self):
        """Clear all highlights"""
        for item in self.highlighted_items:
            self.item(item, tags=())
        self.highlighted_items.clear()


class TruthTableGenerator:
    """Main application class with enhanced GUI and visualizations"""

    def __init__(self, root):
        self.root = root
        self.root.title("🎯 Advanced Truth Table Generator with 3D Visualizations")
        self.root.geometry("1600x1000")

        # Configure dark theme
        self.setup_theme()

        self.current_expression = None
        self.truth_table_data = []
        self.animation_running = False
        self.animation_thread = None
        self.animation_speed = 0.5  # seconds per step
        self.canvas = None
        self.toolbar = None

        self.setup_gui()

        # Bind window events
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def setup_theme(self):
        """Setup the modern dark theme"""
        style = ttk.Style()
        style.theme_use('clam')

        # Configure colors
        bg_color = '#1e1e1e'
        fg_color = '#ffffff'
        accent_color = '#00e5ff'
        secondary_bg = '#252526'
        success_color = '#4CAF50'
        warning_color = '#FF9800'

        # Configure styles
        style.configure('TFrame', background=bg_color)
        style.configure('TLabel', background=bg_color, foreground=fg_color, font=('Segoe UI', 10))
        style.configure('TButton', background=secondary_bg, foreground=fg_color,
                        borderwidth=1, font=('Segoe UI', 10, 'bold'))
        style.map('TButton',
                  background=[('active', accent_color), ('pressed', accent_color)],
                  foreground=[('active', '#000000'), ('pressed', '#000000')])
        style.configure('TEntry', fieldbackground=secondary_bg, foreground=fg_color,
                        insertcolor=accent_color)
        style.configure('TLabelFrame', background=bg_color, foreground=accent_color)
        style.configure('TLabelFrame.Label', background=bg_color, foreground=accent_color,
                        font=('Segoe UI', 11, 'bold'))

        self.root.configure(bg=bg_color)

    def setup_gui(self):
        """Setup the enhanced GUI components"""
        # Main container with gradient effect
        main_container = ttk.Frame(self.root)
        main_container.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)

        # Header section
        header_frame = ttk.Frame(main_container)
        header_frame.pack(fill=tk.X, pady=(0, 15))

        # Title with icon
        title_label = tk.Label(header_frame,
                               text="🔮 Truth Table Generator Pro",
                               font=("Segoe UI", 28, "bold"),
                               fg="#00e5ff",
                               bg="#1e1e1e")
        title_label.pack(side=tk.LEFT)

        # Status indicator
        self.status_indicator = tk.Canvas(header_frame, width=20, height=20,
                                          bg="#1e1e1e", highlightthickness=0)
        self.status_indicator.pack(side=tk.RIGHT, padx=10)
        self.status_light = self.status_indicator.create_oval(2, 2, 18, 18, fill="#4CAF50")

        self.status_var = tk.StringVar(value="🟢 Ready")
        status_label = tk.Label(header_frame, textvariable=self.status_var,
                                font=("Segoe UI", 10), fg="#888", bg="#1e1e1e")
        status_label.pack(side=tk.RIGHT)

        # Input section with modern design
        input_frame = ttk.LabelFrame(main_container, text="📝 Expression Input", padding=20)
        input_frame.pack(fill=tk.X, pady=(0, 15))

        # Expression input with placeholder
        input_container = ttk.Frame(input_frame)
        input_container.pack(fill=tk.X, pady=(0, 15))

        tk.Label(input_container,
                 text="Enter logical expression:",
                 font=("Segoe UI", 11, "bold"),
                 fg="#00e5ff",
                 bg="#1e1e1e").pack(anchor=tk.W)

        self.expression_var = tk.StringVar()
        self.expression_entry = tk.Entry(input_container,
                                         textvariable=self.expression_var,
                                         font=("Consolas", 13),
                                         bg="#252526",
                                         fg="white",
                                         insertbackground="#00e5ff",
                                         relief=tk.FLAT,
                                         highlightthickness=2,
                                         highlightcolor="#00e5ff",
                                         highlightbackground="#333")
        self.expression_entry.pack(fill=tk.X, pady=8)
        self.expression_entry.bind('<Return>', lambda e: self.generate_truth_table())

        # Placeholder text
        self.expression_entry.insert(0, "Example: A AND (B OR NOT C)")
        self.expression_entry.config(fg='#888')
        self.expression_entry.bind('<FocusIn>', self.on_entry_focus_in)
        self.expression_entry.bind('<FocusOut>', self.on_entry_focus_out)

        # Control buttons with icons
        control_frame = ttk.Frame(input_frame)
        control_frame.pack(fill=tk.X)

        button_config = {
            'style': 'Accent.TButton',
            'padding': (20, 10)
        }

        ttk.Button(control_frame, text="🚀 Generate Truth Table",
                   command=self.generate_truth_table, **button_config).pack(side=tk.LEFT, padx=5)

        ttk.Button(control_frame, text="🎬 Animate Evaluation",
                   command=self.toggle_animation, **button_config).pack(side=tk.LEFT, padx=5)

        ttk.Button(control_frame, text="📊 3D Visualization",
                   command=self.show_3d_visualization, **button_config).pack(side=tk.LEFT, padx=5)

        ttk.Button(control_frame, text="⚡ Quick Examples",
                   command=self.show_examples, **button_config).pack(side=tk.LEFT, padx=5)

        ttk.Button(control_frame, text="🗑️ Clear All",
                   command=self.clear_all, **button_config).pack(side=tk.LEFT, padx=5)

        # Speed control for animation
        speed_frame = ttk.Frame(input_frame)
        speed_frame.pack(fill=tk.X, pady=(10, 0))

        tk.Label(speed_frame, text="Animation Speed:",
                 font=("Segoe UI", 9), fg="#aaa", bg="#1e1e1e").pack(side=tk.LEFT)

        self.speed_var = tk.DoubleVar(value=0.5)
        speed_slider = ttk.Scale(speed_frame, from_=0.1, to=2.0, variable=self.speed_var,
                                 orient=tk.HORIZONTAL, length=150)
        speed_slider.pack(side=tk.LEFT, padx=10)

        self.speed_label = tk.Label(speed_frame, text="0.5s",
                                    font=("Segoe UI", 9), fg="#aaa", bg="#1e1e1e")
        self.speed_label.pack(side=tk.LEFT)
        self.speed_var.trace('w', self.update_speed_label)

        # Quick examples bar
        examples_bar = ttk.Frame(main_container)
        examples_bar.pack(fill=tk.X, pady=(0, 15))

        examples = [
            ("Tautology", "A OR NOT A", "#4CAF50"),
            ("Contradiction", "A AND NOT A", "#F44336"),
            ("De Morgan", "NOT (A AND B) IFF (NOT A OR NOT B)", "#2196F3"),
            ("Implication", "A IMPLIES B", "#FF9800"),
            ("XOR", "(A OR B) AND NOT (A AND B)", "#9C27B0"),
            ("Complex", "(A AND B) OR (NOT A AND C)", "#00BCD4")
        ]

        for name, expr, color in examples:
            btn = tk.Button(examples_bar, text=name,
                            command=lambda e=expr: self.load_example(e),
                            bg=color, fg='white',
                            font=("Segoe UI", 9, "bold"),
                            relief=tk.FLAT, padx=12, pady=6,
                            cursor="hand2")
            btn.pack(side=tk.LEFT, padx=2)
            btn.bind("<Enter>", lambda e, b=btn: b.config(bg='white', fg='black'))
            btn.bind("<Leave>", lambda e, b=btn, c=color: b.config(bg=c, fg='white'))

        # Main content area
        content_frame = ttk.Frame(main_container)
        content_frame.pack(fill=tk.BOTH, expand=True)

        # Left panel - Truth Table
        left_panel = ttk.LabelFrame(content_frame, text="📋 Truth Table", padding=10)
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))

        # Create enhanced treeview
        tree_frame = ttk.Frame(left_panel)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        # Add scrollbars
        v_scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL)
        h_scrollbar = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL)

        self.tree = EnhancedTreeview(tree_frame,
                                     yscrollcommand=v_scrollbar.set,
                                     xscrollcommand=h_scrollbar.set,
                                     style="Treeview")

        v_scrollbar.config(command=self.tree.yview)
        h_scrollbar.config(command=self.tree.xview)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)

        # Configure treeview style
        style = ttk.Style()
        style.configure("Treeview",
                        background="#252526",
                        foreground="white",
                        fieldbackground="#252526",
                        rowheight=35)
        style.configure("Treeview.Heading",
                        background="#1e1e1e",
                        foreground="#00e5ff",
                        font=('Segoe UI', 10, 'bold'))
        style.map('Treeview',
                  background=[('selected', '#00e5ff')],
                  foreground=[('selected', 'black')])

        # Right panel - Analysis
        right_panel = ttk.LabelFrame(content_frame, text="📈 Analysis & Visualization", padding=10)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))

        # Create notebook for tabs
        self.notebook = ttk.Notebook(right_panel)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # Analysis tab
        analysis_tab = ttk.Frame(self.notebook)
        self.notebook.add(analysis_tab, text="📊 Analysis")

        self.analysis_text = scrolledtext.ScrolledText(analysis_tab,
                                                       bg="#252526",
                                                       fg="white",
                                                       font=("Consolas", 10),
                                                       insertbackground="white",
                                                       relief=tk.FLAT)
        self.analysis_text.pack(fill=tk.BOTH, expand=True)

        # Visualization tab
        viz_tab = ttk.Frame(self.notebook)
        self.notebook.add(viz_tab, text="🎨 Visualization")

        self.viz_canvas_frame = ttk.Frame(viz_tab)
        self.viz_canvas_frame.pack(fill=tk.BOTH, expand=True)

        # Progress bar for animation
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(main_container,
                                            variable=self.progress_var,
                                            maximum=100,
                                            mode='determinate',
                                            style="TProgressbar")
        self.progress_bar.pack(fill=tk.X, pady=(10, 0))

    def on_entry_focus_in(self, event):
        """Handle focus in event for entry"""
        if self.expression_entry.get() == "Example: A AND (B OR NOT C)":
            self.expression_entry.delete(0, tk.END)
            self.expression_entry.config(fg='white')

    def on_entry_focus_out(self, event):
        """Handle focus out event for entry"""
        if not self.expression_entry.get():
            self.expression_entry.insert(0, "Example: A AND (B OR NOT C)")
            self.expression_entry.config(fg='#888')

    def update_speed_label(self, *args):
        """Update speed label"""
        self.animation_speed = self.speed_var.get()
        self.speed_label.config(text=f"{self.animation_speed:.1f}s")

    def load_example(self, expression):
        """Load an example expression"""
        self.expression_var.set(expression)
        self.expression_entry.config(fg='white')
        self.generate_truth_table()

    def show_examples(self):
        """Show examples dialog"""
        examples_window = tk.Toplevel(self.root)
        examples_window.title("📚 Quick Examples")
        examples_window.geometry("500x400")
        examples_window.configure(bg='#1e1e1e')
        examples_window.transient(self.root)
        examples_window.grab_set()

        examples = [
            ("Basic AND", "A AND B", "Logical conjunction"),
            ("Basic OR", "A OR B", "Logical disjunction"),
            ("Negation", "NOT A", "Logical negation"),
            ("Implication", "A IMPLIES B", "Conditional statement"),
            ("Biconditional", "A IFF B", "If and only if"),
            ("De Morgan 1", "NOT (A AND B)", "Equivalent to NOT A OR NOT B"),
            ("De Morgan 2", "NOT (A OR B)", "Equivalent to NOT A AND NOT B"),
            ("XOR", "(A OR B) AND NOT (A AND B)", "Exclusive OR"),
            ("Tautology", "A OR NOT A", "Always true"),
            ("Contradiction", "A AND NOT A", "Always false"),
        ]

        for name, expr, desc in examples:
            frame = tk.Frame(examples_window, bg='#252526', relief=tk.RAISED, bd=1)
            frame.pack(fill=tk.X, padx=10, pady=5)

            tk.Label(frame, text=name, font=("Segoe UI", 11, "bold"),
                     fg="#00e5ff", bg='#252526').pack(anchor=tk.W)
            tk.Label(frame, text=expr, font=("Consolas", 10),
                     fg="white", bg='#252526').pack(anchor=tk.W)
            tk.Label(frame, text=desc, font=("Segoe UI", 9),
                     fg="#aaa", bg='#252526').pack(anchor=tk.W)

            tk.Button(frame, text="Use", command=lambda e=expr: self.use_example(e, examples_window),
                      bg="#4CAF50", fg="white", relief=tk.FLAT, padx=15).pack(side=tk.RIGHT)

    def use_example(self, expression, window):
        """Use selected example"""
        self.expression_var.set(expression)
        self.expression_entry.config(fg='white')
        window.destroy()
        self.generate_truth_table()

    def generate_truth_table(self):
        """Generate and display truth table"""
        expression_text = self.expression_var.get().strip()
        if not expression_text or expression_text == "Example: A AND (B OR NOT C)":
            messagebox.showwarning("Input Required", "Please enter a logical expression!")
            return

        try:
            self.current_expression = LogicalExpression(expression_text)
            self.create_truth_table()
            self.analyze_expression()
            self.status_var.set(f"✅ Generated truth table for: {expression_text}")
            self.update_status_light("#4CAF50")
        except Exception as e:
            messagebox.showerror("Expression Error", f"Error parsing expression: {str(e)}")
            self.update_status_light("#F44336")

    def update_status_light(self, color):
        """Update the status light color"""
        self.status_indicator.itemconfig(self.status_light, fill=color)

    def create_truth_table(self):
        """Create the truth table data and display"""
        if not self.current_expression:
            return

        variables = self.current_expression.variables
        n_vars = len(variables)

        # Clear existing tree
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Setup columns
        columns = variables + ["Result"]
        self.tree["columns"] = columns
        self.tree["show"] = "headings"

        for col in columns:
            self.tree.heading(col, text=col, anchor=tk.CENTER)
            self.tree.column(col, width=100, anchor=tk.CENTER)

        # Generate all combinations
        self.truth_table_data = []
        for combination in itertools.product([False, True], repeat=n_vars):
            var_dict = dict(zip(variables, combination))
            result = self.current_expression.evaluate(var_dict)

            row = [int(val) for val in combination] + [result]
            self.truth_table_data.append(row)

            # Add to tree with color coding
            item = self.tree.insert("", tk.END, values=row, tags=('normal',))

            # Color code based on result
            if result == 1:
                self.tree.tag_configure('true', background='#1B5E20', foreground='white')
                self.tree.item(item, tags=('true',))
            else:
                self.tree.tag_configure('false', background='#B71C1C', foreground='white')
                self.tree.item(item, tags=('false',))

        # Add summary row (separate from data rows)
        if self.truth_table_data:
            true_count = sum(row[-1] for row in self.truth_table_data)
            total_count = len(self.truth_table_data)
            summary_text = f"True: {true_count}/{total_count} ({true_count / total_count:.1%})"

            summary_item = self.tree.insert("", tk.END,
                                            values=["" for _ in range(n_vars)] + [summary_text],
                                            tags=('summary',))
            self.tree.tag_configure('summary', background='#37474F', foreground='#00e5ff',
                                    font=('Segoe UI', 10, 'bold'))

    def analyze_expression(self):
        """Analyze the expression for tautologies, contradictions, etc."""
        if not self.truth_table_data:
            return

        results = [row[-1] for row in self.truth_table_data]
        true_count = sum(results)
        total_count = len(results)
        false_count = total_count - true_count

        analysis = f"🔍 LOGICAL EXPRESSION ANALYSIS\n"
        analysis += f"{'=' * 40}\n\n"

        analysis += f"📝 Expression: {self.current_expression.expression}\n"
        analysis += f"🔤 Variables: {', '.join(self.current_expression.variables)}\n"
        analysis += f"📊 Total combinations: {total_count}\n\n"

        # Statistics with progress bars
        true_percent = true_count / total_count * 100
        false_percent = false_count / total_count * 100

        analysis += f"✅ True assignments: {true_count}\n"
        analysis += f"   █" * int(true_percent / 5) + f" {true_percent:.1f}%\n\n"

        analysis += f"❌ False assignments: {false_count}\n"
        analysis += f"   █" * int(false_percent / 5) + f" {false_percent:.1f}%\n\n"

        # Classification with emojis
        analysis += "🏷️  CLASSIFICATION:\n"
        if true_count == total_count:
            analysis += "   🟢 TAUTOLOGY (always true)\n"
            analysis += "   📝 All possible assignments yield True\n\n"
        elif false_count == total_count:
            analysis += "   🔴 CONTRADICTION (always false)\n"
            analysis += "   📝 All possible assignments yield False\n\n"
        else:
            analysis += "   🟡 CONTINGENCY\n"
            analysis += "   📝 Expression depends on variable values\n\n"

        # Satisfiability
        analysis += "🔍 SATISFIABILITY:\n"
        if true_count > 0:
            analysis += "   ✅ SATISFIABLE\n"
            analysis += "   📊 Satisfying assignments found\n\n"

            # Show first few satisfying assignments
            analysis += "   📋 Satisfying assignments:\n"
            count = 0
            for i, row in enumerate(self.truth_table_data):
                if row[-1] == 1 and count < 5:
                    assignment = ", ".join(f"{var}={val}"
                                           for var, val in zip(self.current_expression.variables, row[:-1]))
                    analysis += f"   • {assignment}\n"
                    count += 1
            if true_count > 5:
                analysis += f"   ... and {true_count - 5} more\n\n"
        else:
            analysis += "   ❌ UNSATISFIABLE\n"
            analysis += "   📊 No satisfying assignments exist\n\n"

        # Logical properties
        analysis += "⚡ LOGICAL PROPERTIES:\n"
        if len(self.current_expression.variables) == 2:
            pattern = self.identify_binary_operation()
            analysis += f"   • {pattern}\n"

        # Complexity
        analysis += f"\n📈 Expression complexity: {'★' * min(len(self.current_expression.variables), 5)}\n"

        self.analysis_text.delete(1.0, tk.END)
        self.analysis_text.insert(1.0, analysis)

    def identify_binary_operation(self):
        """Identify the type of binary operation"""
        results = [row[-1] for row in self.truth_table_data]

        operations = {
            (0, 0, 0, 0): "Contradiction (False)",
            (0, 0, 0, 1): "Conjunction (AND)",
            (0, 0, 1, 0): "Material non-implication",
            (0, 0, 1, 1): "First projection",
            (0, 1, 0, 0): "Converse non-implication",
            (0, 1, 0, 1): "Second projection",
            (0, 1, 1, 0): "Exclusive disjunction (XOR)",
            (0, 1, 1, 1): "Disjunction (OR)",
            (1, 0, 0, 0): "Joint denial (NOR)",
            (1, 0, 0, 1): "Biconditional (XNOR)",
            (1, 0, 1, 0): "Negation (NOT B)",
            (1, 0, 1, 1): "Converse implication",
            (1, 1, 0, 0): "Negation (NOT A)",
            (1, 1, 0, 1): "Material implication",
            (1, 1, 1, 0): "Alternative denial (NAND)",
            (1, 1, 1, 1): "Tautology (True)"
        }

        pattern = tuple(results)
        return operations.get(pattern, "Custom operation")

    def toggle_animation(self):
        """Toggle animation on/off"""
        if self.animation_running:
            self.stop_animation()
        else:
            self.start_animation()

    def start_animation(self):
        """Start animated evaluation of the truth table"""
        if not self.current_expression or not self.truth_table_data:
            messagebox.showinfo("Animation", "Please generate a truth table first!")
            return

        if self.animation_running:
            return

        self.animation_running = True
        self.update_status_light("#FF9800")
        self.status_var.set("🎬 Animation running...")

        self.progress_var.set(0)
        self.tree.clear_highlights()

        # Start animation in separate thread
        self.animation_thread = threading.Thread(target=self.run_animation, daemon=True)
        self.animation_thread.start()

    def run_animation(self):
        """Run the animation sequence"""
        items = list(self.tree.get_children())

        # Filter out summary row from animation items
        animation_items = []
        animation_data_indices = []

        for i, item in enumerate(items):
            # Skip summary row (last item)
            if i < len(self.truth_table_data):
                animation_items.append(item)
                animation_data_indices.append(i)

        total_items = len(animation_items)

        for idx, (item, data_idx) in enumerate(zip(animation_items, animation_data_indices)):
            if not self.animation_running:
                break

            # Update progress
            progress = (idx + 1) / total_items * 100
            self.root.after(0, lambda p=progress: self.progress_var.set(p))

            # Get row data (use data_idx to access truth_table_data)
            if data_idx < len(self.truth_table_data):
                row_data = self.truth_table_data[data_idx]

                # Highlight current row with animation effect
                self.root.after(0, lambda it=item, i=idx: self.animate_row(it, i))

                # Show evaluation info
                assignment = ", ".join(f"{var}={val}"
                                       for var, val in zip(self.current_expression.variables, row_data[:-1]))

                result_text = "✅ True" if row_data[-1] == 1 else "❌ False"
                status_text = f"🎬 Step {idx + 1}/{total_items}: {assignment} → {result_text}"
                self.root.after(0, lambda st=status_text: self.status_var.set(st))

                time.sleep(self.animation_speed)

                # Remove highlight after delay
                if idx < total_items - 1:
                    time.sleep(0.1)
                    self.root.after(0, lambda it=item: self.tree.item(it, tags=()))

        if self.animation_running:
            self.root.after(0, self.animation_complete)

    def animate_row(self, item, step):
        """Animate a single row highlight"""
        # Calculate color based on step (rainbow effect)
        hue = (step * 60) % 360
        color = self.hsl_to_hex(hue, 70, 50)

        self.tree.highlight_row(item, color)
        self.tree.see(item)
        self.tree.selection_set(item)

    def hsl_to_hex(self, h, s, l):
        """Convert HSL color to hex"""
        h /= 360.0
        s /= 100.0
        l /= 100.0

        if s == 0:
            r = g = b = l
        else:
            def hue_to_rgb(p, q, t):
                if t < 0: t += 1
                if t > 1: t -= 1
                if t < 1 / 6: return p + (q - p) * 6 * t
                if t < 1 / 2: return q
                if t < 2 / 3: return p + (q - p) * (2 / 3 - t) * 6
                return p

            q = l * (1 + s) if l < 0.5 else l + s - l * s
            p = 2 * l - q

            r = hue_to_rgb(p, q, h + 1 / 3)
            g = hue_to_rgb(p, q, h)
            b = hue_to_rgb(p, q, h - 1 / 3)

        r = int(r * 255)
        g = int(g * 255)
        b = int(b * 255)

        return f'#{r:02x}{g:02x}{b:02x}'

    def animation_complete(self):
        """Handle animation completion"""
        self.animation_running = False
        self.status_var.set("✅ Animation complete!")
        self.update_status_light("#4CAF50")

        # Flash all true rows
        items = list(self.tree.get_children())
        for i, item in enumerate(items):
            if i < len(self.truth_table_data) and self.truth_table_data[i][-1] == 1:
                self.tree.highlight_row(item, "#4CAF50")

        # Show completion message
        messagebox.showinfo("Animation Complete",
                            "Animation finished! All true assignments are highlighted in green.")

    def stop_animation(self):
        """Stop the animation"""
        self.animation_running = False
        self.status_var.set("⏹️ Animation stopped")
        self.update_status_light("#F44336")
        self.progress_var.set(0)

    def show_3d_visualization(self):
        """Show 3D visualization of the truth table"""
        if not self.current_expression or not self.truth_table_data:
            messagebox.showinfo("Visualization",
                                "Please generate a truth table first!")
            return

        self.create_3d_plot()

    def create_3d_plot(self):
        """Create enhanced 3D plot of truth table data"""
        plt.close('all')

        # Clear previous canvas
        for widget in self.viz_canvas_frame.winfo_children():
            widget.destroy()

        n_vars = len(self.current_expression.variables)

        if n_vars == 1:
            self.create_1d_visualization()
        elif n_vars == 2:
            self.create_2d_3d_plot()
        elif n_vars == 3:
            self.create_3d_cube_plot()
        else:
            self.create_hypercube_projection()

    def create_1d_visualization(self):
        """Create visualization for 1 variable"""
        fig = plt.figure(figsize=(10, 6), facecolor='#1e1e1e', dpi=100)
        ax = fig.add_subplot(111, facecolor='#1e1e1e')

        # Create bar chart
        x = [0, 1]
        results = [0, 0]

        for row in self.truth_table_data:
            results[row[0]] = row[-1]  # Store the result for each input

        colors = ['#F44336' if r == 0 else '#4CAF50' for r in results]
        bars = ax.bar(x, [1, 1], color=colors, alpha=0.7, width=0.6)

        # Add value labels
        for i, (bar, r) in enumerate(zip(bars, results)):
            color = 'white' if results[i] == 1 else '#aaa'
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.1,
                    f"f({i}) = {r}", ha='center', va='bottom',
                    color=color, fontweight='bold', fontsize=12)

        ax.set_xlabel(f'Value of {self.current_expression.variables[0]}', color='white', fontsize=12)
        ax.set_ylabel('Truth Value', color='white', fontsize=12)
        ax.set_title(f'Truth Table for {self.current_expression.expression}',
                     color='white', fontsize=14, fontweight='bold')

        ax.set_xticks(x)
        ax.set_xticklabels(['False (0)', 'True (1)'], color='white', fontsize=11)
        ax.set_ylim(0, 1.5)
        ax.tick_params(colors='white')
        ax.grid(True, alpha=0.3, color='#444')

        self.embed_plot(fig)

    def create_2d_3d_plot(self):
        """Create 3D visualization for 2 variables"""
        fig = plt.figure(figsize=(12, 8), facecolor='#1e1e1e', dpi=100)
        ax = fig.add_subplot(111, projection='3d', facecolor='#1e1e1e')

        # Create grid
        x = np.array([0, 0, 1, 1])
        y = np.array([0, 1, 0, 1])
        z = np.array([row[-1] for row in self.truth_table_data])

        # Color points based on truth value with gradient
        colors = ['#F44336' if val == 0 else '#4CAF50' for val in z]
        sizes = [300 if val == 1 else 200 for val in z]

        # Create 3D scatter plot
        scatter = ax.scatter(x, y, z, c=colors, s=sizes, alpha=0.8,
                             edgecolors='white', linewidth=2, depthshade=True)

        # Create connecting lines
        for i in range(len(x)):
            ax.plot([x[i], x[i]], [y[i], y[i]], [0, z[i]],
                    color=colors[i], linewidth=3, alpha=0.6, linestyle='--')

        # Create surface if we have all points
        if len(x) == 4:
            X, Y = np.meshgrid([0, 1], [0, 1])
            Z = np.array(z).reshape(2, 2)
            surf = ax.plot_surface(X, Y, Z, alpha=0.3, cmap='RdYlGn',
                                   edgecolor='white', linewidth=0.5)

        # Add labels with truth values
        for i, (xi, yi, zi) in enumerate(zip(x, y, z)):
            label = f"{int(zi)}"
            ax.text(xi, yi, zi + 0.1, label, color='white',
                    fontsize=12, fontweight='bold', ha='center')

        ax.set_xlabel(self.current_expression.variables[0], color='white', fontsize=12)
        ax.set_ylabel(self.current_expression.variables[1], color='white', fontsize=12)
        ax.set_zlabel('Truth Value', color='white', fontsize=12)

        title = f'3D Truth Space: {self.current_expression.expression}'
        ax.set_title(title, color='white', fontsize=14, fontweight='bold', pad=20)

        # Style the plot
        ax.tick_params(colors='white')
        ax.xaxis.label.set_color('white')
        ax.yaxis.label.set_color('white')
        ax.zaxis.label.set_color('white')

        # Set view angle
        ax.view_init(elev=20, azim=45)

        # Set axis limits
        ax.set_xlim(-0.5, 1.5)
        ax.set_ylim(-0.5, 1.5)
        ax.set_zlim(-0.1, 1.1)

        self.embed_plot(fig)

    def create_3d_cube_plot(self):
        """Create 3D cube visualization for 3 variables"""
        fig = plt.figure(figsize=(12, 8), facecolor='#1e1e1e', dpi=100)
        ax = fig.add_subplot(111, projection='3d', facecolor='#1e1e1e')

        vertices = []
        colors = []

        for row in self.truth_table_data:
            x, y, z = row[:3]
            result = row[-1]
            vertices.append([x, y, z])
            colors.append('#4CAF50' if result == 1 else '#F44336')

        vertices = np.array(vertices)

        # Plot vertices
        scatter = ax.scatter(vertices[:, 0], vertices[:, 1], vertices[:, 2],
                             c=colors, s=400, alpha=0.8, edgecolors='white', linewidth=2, depthshade=True)

        # Draw cube edges
        edges = [
            [0, 1], [0, 2], [0, 4], [1, 3], [1, 5], [2, 3],
            [2, 6], [3, 7], [4, 5], [4, 6], [5, 7], [6, 7]
        ]

        for edge in edges:
            points = vertices[edge]
            ax.plot3D(*points.T, 'white', alpha=0.3, linewidth=1, linestyle=':')

        # Label vertices with their truth values
        for i, (vertex, color, row) in enumerate(zip(vertices, colors, self.truth_table_data)):
            ax.text(vertex[0], vertex[1], vertex[2] + 0.1,
                    str(row[-1]), color=color, fontsize=12, fontweight='bold', ha='center')

        ax.set_xlabel(self.current_expression.variables[0], color='white', fontsize=12)
        ax.set_ylabel(self.current_expression.variables[1], color='white', fontsize=12)
        ax.set_zlabel(self.current_expression.variables[2], color='white', fontsize=12)

        title = f'3D Truth Cube: {self.current_expression.expression}'
        ax.set_title(title, color='white', fontsize=14, fontweight='bold', pad=20)

        # Style the plot
        ax.tick_params(colors='white')
        ax.xaxis.label.set_color('white')
        ax.yaxis.label.set_color('white')
        ax.zaxis.label.set_color('white')

        # Set view angle
        ax.view_init(elev=25, azim=45)

        self.embed_plot(fig)

    def create_hypercube_projection(self):
        """Create hypercube projection for 4+ variables"""
        fig = plt.figure(figsize=(12, 8), facecolor='#1e1e1e', dpi=100)
        ax = fig.add_subplot(111, projection='3d', facecolor='#1e1e1e')

        n_vars = len(self.current_expression.variables)

        # Create positions using multidimensional scaling
        positions = []
        colors = []
        sizes = []

        for row in self.truth_table_data:
            # Use PCA-like projection to 3D
            if n_vars >= 3:
                # Weighted sum for projection
                x = row[0] * 1.0 + row[1] * 0.5 + row[2] * 0.2
                y = row[1] * 1.0 + row[0] * 0.5 + row[2] * 0.2
                z = row[2] * 1.0 + row[0] * 0.2 + row[1] * 0.2

                # Add contribution from other variables
                for i in range(3, min(n_vars, 6)):
                    weight = 0.1 / (i - 1)
                    x += row[i] * weight
                    y += row[i] * weight * 0.7
                    z += row[i] * weight * 0.3
            else:
                x, y, z = row[0], row[1] if n_vars > 1 else 0, 0

            positions.append([x, y, z])
            colors.append('#4CAF50' if row[-1] == 1 else '#F44336')
            sizes.append(300 if row[-1] == 1 else 200)

        positions = np.array(positions)

        # Create scatter plot
        scatter = ax.scatter(positions[:, 0], positions[:, 1], positions[:, 2],
                             c=colors, s=sizes, alpha=0.8, edgecolors='white', linewidth=2, depthshade=True)

        ax.set_xlabel('Dimension 1', color='white', fontsize=12)
        ax.set_ylabel('Dimension 2', color='white', fontsize=12)
        ax.set_zlabel('Dimension 3', color='white', fontsize=12)

        title = f'Hypercube Projection ({n_vars}D → 3D)'
        ax.set_title(title, color='white', fontsize=14, fontweight='bold', pad=20)

        # Style the plot
        ax.tick_params(colors='white')
        ax.xaxis.label.set_color('white')
        ax.yaxis.label.set_color('white')
        ax.zaxis.label.set_color('white')

        # Set view angle
        ax.view_init(elev=20, azim=30)

        self.embed_plot(fig)

    def embed_plot(self, fig):
        """Embed matplotlib plot in tkinter"""
        if self.canvas:
            try:
                self.canvas.get_tk_widget().destroy()
            except:
                pass

        self.canvas = FigureCanvasTkAgg(fig, self.viz_canvas_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Add toolbar
        if self.toolbar:
            try:
                self.toolbar.destroy()
            except:
                pass

        self.toolbar = NavigationToolbar2Tk(self.canvas, self.viz_canvas_frame)
        self.toolbar.update()
        self.toolbar.pack(side=tk.BOTTOM, fill=tk.X)

        # Switch to visualization tab
        self.notebook.select(1)  # Index 1 is the visualization tab

    def clear_all(self):
        """Clear all data and reset the interface"""
        self.expression_var.set("")
        self.current_expression = None
        self.truth_table_data = []

        # Stop any running animation
        self.stop_animation()

        # Clear tree
        self.tree.clear_highlights()
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Clear analysis
        self.analysis_text.delete(1.0, tk.END)

        # Clear visualization
        for widget in self.viz_canvas_frame.winfo_children():
            widget.destroy()

        # Reset progress
        self.progress_var.set(0)

        # Reset status
        self.status_var.set("🟢 Ready")
        self.update_status_light("#4CAF50")

        # Reset placeholder
        self.expression_entry.delete(0, tk.END)
        self.expression_entry.insert(0, "Example: A AND (B OR NOT C)")
        self.expression_entry.config(fg='#888')

    def on_closing(self):
        """Handle window closing"""
        self.stop_animation()
        self.root.quit()
        self.root.destroy()


def main():
    """Main function to run the application"""
    root = tk.Tk()

    # Set application icon (optional)
    try:
        root.iconbitmap('icon.ico')
    except:
        pass

    app = TruthTableGenerator(root)

    # Add welcome message
    welcome_message = """
    ⭐ WELCOME TO TRUTH TABLE GENERATOR PRO ⭐

    ░▒▓█▶ Features ◀█▓▒░

    🎯 Expression Parsing
    • Support for AND, OR, NOT, IMPLIES, IFF
    • Complex expressions with parentheses
    • Real-time error checking

    📊 Truth Table Generation
    • Color-coded results (Green=True, Red=False)
    • Auto-detection of patterns
    • Statistics and analysis

    🎬 Animated Evaluation
    • Step-by-step visualization
    • Adjustable animation speed
    • Rainbow highlighting effect

    📈 3D Visualizations
    • 1D, 2D, and 3D plots
    • Hypercube projections
    • Interactive viewing

    🎨 Modern Interface
    • Dark theme with neon accents
    • Smooth animations
    • Responsive design

    ░▒▓█▶ Quick Start ◀█▓▒░

    1. Enter an expression in the input field
    2. Click 'Generate Truth Table' or press Enter
    3. Explore the results in the table
    4. Use 'Animate Evaluation' to see step-by-step
    5. Switch to 'Visualization' tab for 3D plots

    Try these examples:
    • A OR NOT A (Tautology)
    • A AND NOT A (Contradiction)
    • A IMPLIES B (Implication)
    • (A AND B) OR (NOT A AND C) (Complex)

    ⚡ Tip: Use the 'Quick Examples' button for more!
    """

    app.analysis_text.insert(1.0, welcome_message)

    # Center window on screen
    root.update_idletasks()
    width = root.winfo_width()
    height = root.winfo_height()
    x = (root.winfo_screenwidth() // 2) - (width // 2)
    y = (root.winfo_screenheight() // 2) - (height // 2)
    root.geometry(f'{width}x{height}+{x}+{y}')

    root.mainloop()


if __name__ == "__main__":
    main()