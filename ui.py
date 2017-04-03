"""This file implements the UI, using the helper modules."""
import command_parser
import sonifier
import sympy
from sympy.utilities import lambdify
from sympy.parsing import sympy_parser

class Ui(command_parser.CommandParserBase):

    prompt = "y = "

    def __init__(self):
        self.min_x = 0
        self.max_x = 10
        self.min_y = 0
        self.max_y = 10
        self.duration = 5.0
        self.hrtf = False
        self.x_symbol, self.y_symbol = sympy.symbols("x, y")
        self.current_graph = None

    def do_default(self, argument):
        print("Graphing ", argument)
        sym = sympy_parser.parse_expr(argument, transformations = 
            sympy_parser.standard_transformations + (sympy_parser.split_symbols, sympy_parser.implicit_multiplication,
                sympy_parser.function_exponentiation))
        f = lambdify((self.x_symbol, ), sym)
        if self.current_graph is not None:
            self.current_graph.shutdown()
        self.current_graph = sonifier.Sonifier(f = f, duration = self.duration, min_x = self.min_x,
            max_x = self.max_x, min_y = self.min_y, max_y = self.max_y,
            hrtf = self.hrtf)
        self.current_graph.to_audio_device()
