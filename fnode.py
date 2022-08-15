from enum import IntEnum
import numpy as np
from PyQt6.QtCore import QObject, pyqtSignal
import json
import re
import gc

from options import CURVE_FRAMES, CURVE_RESOLUTION


class FNode(QObject):
	ID_COUNTER = 0
	ACTIVE_NODES = {}
	PAUSE_CALCULATIONS = False

	nodeStateChanged = pyqtSignal(object, int)

	class Type(IntEnum):
		NULL = 0
		CONSTANT = 1
		PI = 2
		E = 3
		W = 10
		X = 11
		Y = 12
		Z = 13
		AND = 100
		OR = 110
		NOT_EQUAL = 140
		EQUAL = 141
		GREATER_EQ = 142
		LESS_EQ = 143
		GREATER_THAN = 144
		LESS_THAN = 145
		ADD = 150
		SUBTRACT = 151
		MULTIPLY = 160
		DIVIDE = 161
		EXPONENT = 170
		SIN = 200
		COS = 201
		TAN = 202
		ASIN = 203
		ACOS = 204
		ATAN = 205
		SINH = 206
		COSH = 207
		TANH = 208
		ASINH = 209
		ACOSH = 210
		ATANH = 211
		LOG2 = 250
		LOG10 = 251
		LN = 252
		SQRT = 253
		SIGN = 254
		RINT = 255
		ABS = 256
		MIN = 290
		MAX = 291
		SUM = 292
		AVG = 293
		NEGATE = 300
		OPEN_PAREN = 350
		CLOSE_PAREN = 351
		VARIABLE = 400
		FN_PARAMETER = 500
		SET = 600
		FUNCTION = 700
		ROOT = 999
	

	class State(IntEnum):
		INVALID = 0
		VALID = 1
		CALCULATED = 2
		N_CHILDREN_OVER = 2
		N_CHILDREN_UNDER = 3
		INVALID_DESCENDANT = 4


	def __init__(self, type:'FNode.Type'):
		super().__init__()
		self._nodeID = FNode.ID_COUNTER
		FNode.ID_COUNTER += 1
		FNode.ACTIVE_NODES[self._nodeID] = self
		self._type = type
		self._parent = None
		self._children = []
		self._fnVariables = []
		self._negated = False
		self._name = None
		self._value = 0
		self._formula = ''
		self._state = FNode.UNCALCULATED



	def _calcFn(self):
		match self.
		FNodeType.PI: lambda *_: np.pi,
		FNodeType.E: lambda *_: np.e,
		FNodeType.W: lambda *_: np.tile(np.linspace(0, 1, CURVE_RESOLUTION), (CURVE_FRAMES, 1)),
		FNodeType.X: lambda *_: np.tile(np.linspace(-1, 1, CURVE_RESOLUTION), (CURVE_FRAMES, 1)),
		FNodeType.Y: lambda *_: np.repeat(np.linspace(-1, 1, CURVE_FRAMES), CURVE_RESOLUTION).reshape(CURVE_FRAMES, CURVE_RESOLUTION),
		FNodeType.Z: lambda *_: np.repeat(np.linspace(0, 1, CURVE_FRAMES), CURVE_RESOLUTION).reshape(CURVE_FRAMES, CURVE_RESOLUTION),
		FNodeType.SIN: np.sin,
		FNodeType.COS: np.cos,
		FNodeType.TAN: np.tan,
		FNodeType.ASIN: np.arcsin,
		FNodeType.ACOS: np.arccos,
		FNodeType.ATAN: np.arctan,
		FNodeType.SINH: np.sinh,
		FNodeType.COSH: np.cosh,
		FNodeType.TANH: np.tanh,
		FNodeType.ASINH: np.arcsinh,
		FNodeType.ACOSH: np.arccosh,
		FNodeType.ATANH: np.arctanh,
		FNodeType.LOG2: np.log2,
		FNodeType.LOG10: np.log10,
		FNodeType.LN: np.log,
		FNodeType.SQRT: np.sqrt,
		FNodeType.SIGN: np.sign,
		FNodeType.RINT: np.rint,
		FNodeType.ABS: np.abs,
		FNodeType.NEGATE: np.negative,
		FNodeType.ADD: lambda *c: FNode.accumulate(np.add, c),
		FNodeType.SUBTRACT: lambda *c: FNode.accumulate(np.subtract, c),
		FNodeType.MULTIPLY: lambda *c: FNode.accumulate(np.multiply, c),
		FNodeType.DIVIDE: lambda *c: FNode.accumulate(np.divide, c),
		FNodeType.EXPONENT: lambda *c: FNode.accumulate(np.power, c),
		FNodeType.EQUAL: lambda *c: FNode.accumulate(lambda x, y: np.equal(x, y).astype(int), c),
		FNodeType.NOT_EQUAL: lambda *c: 106,
		FNodeType.LESS_THAN: lambda *c: 107,
		FNodeType.LESS_EQ: lambda *c: 108,
		FNodeType.GREATER_THAN: lambda *c: 109,
		FNodeType.GREATER_EQ: lambda *c: 110,
		FNodeType.OR: lambda *c: 111,
		FNodeType.AND: lambda *c: 112,
		FNodeType.MIN: lambda *c: 113,
		FNodeType.MAX: lambda *c: 114,
		FNodeType.SUM: lambda *c: 115,
		FNodeType.AVG: lambda *c: 116