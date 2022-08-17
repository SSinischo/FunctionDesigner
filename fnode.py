from ast import Constant
from enum import IntEnum
from fnmatch import fnmatch
from unittest.loader import VALID_MODULE_NAME
import numpy as np
from PyQt6.QtCore import QObject, pyqtSignal
import json
import re
import gc
import logging as log

from fnode_util import CALC_FUNCTIONS, FORMULA_FUNCTIONS, FORMULA_TOKENS, DISPLAY_NAMES
from options import CURVE_FRAMES, CURVE_RESOLUTION


class FNode(QObject):

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
		OPEN_PAREN = 300
		CLOSE_PAREN = 301
		VARIABLE = 400
		FN_PARAMETER = 500
		SET = 600
		FUNCTION = 700
		ROOT = 999
		NEGATE = 1000


	class State(IntEnum):
		VALID = 1
		CALCULATED = 2
		INVALID = 10
		N_CHILDREN_OVER = 11
		N_CHILDREN_UNDER = 11
		INVALID_DESCENDANT = 12


	ID_COUNTER = 0
	ACTIVE_NODES = {}

	nodeStateChanged = pyqtSignal(object, int)


	def __init__(self, type:'FNode.Type'):
		super().__init__()
		self._nodeID = FNode.ID_COUNTER
		FNode.ID_COUNTER += 1
		FNode.ACTIVE_NODES[self._nodeID] = self
		self._type = type
		self._parent = None
		self._children = []
		self._value = np.pi if self._type == FNode.Type.PI else np.e if self._type == FNode.Type.E else 0
		self._formula = ''
		self._negated = False
		self._state = FNode.State.INVALID
		self._name = ''
		self._parameters = {}
		log.debug(f'{self} - created')


	def __repr__(self) -> str:
		s = f'#{self._nodeID}'
		s2 = self._value if self._type == FNode.Type.CONSTANT else self._name
		return f'{s} {self._type.name} [{s2}]'


	def __str__(self):
		s = f'#{self._nodeID}'
		s2 = self._value if self._type == FNode.Type.CONSTANT else self._name
		return f'{s} {self._type.name} [{s2}] [c{len(self._children)}]'
	

	def expectedChildCount(self):
		if(self._type < 100 or self._type == FNode.Type.VARIABLE):
			return 0
		elif(self._type < 200 or 290 <= self._type < 300 or self._type == FNode.Type.SET):
			return -1
		return 1
	

	def validate(self, childState=None):
		if(self._type == FNode.Type.FUNCTION):
			for k, v in self._parameters.items():
				if(c._state >= FNode.State.INVALID):
					s = FNode.State.INVALID
					break
			s = FNode.State.VALID
		else:
			expChildren = self.expectedChildCount()
			s = FNode.State.CALCULATED if expChildren == 0 else FNode.State.VALID
			if(not childState):
				for c in self._children:
					if(c._state >= FNode.State.INVALID):
						s = FNode.State.INVALID_DESCENDANT
						break
			elif(childState >= FNode.State.INVALID and self._state < FNode.State.INVALID):
				s = FNode.State.INVALID_DESCENDANT
			elif(s != FNode.State.INVALID_DESCENDANT):
				if(expChildren == -1 and not self._children):
					s = FNode.State.N_CHILDREN_UNDER
				elif(len(self._children) > expChildren):
					s = FNode.State.N_CHILDREN_OVER
				elif(len(self._children) < expChildren):
					s = FNode.State.N_CHILDREN_UNDER
		if(self._state != s):
			self._state = s
			self.nodeStateChanged.emit(self)
		if(self._parent):
			self._parent.validate(s)

	

	def value(self):
		if(self._type >= FNode.Type.SET):
			return None
		if(self._state == FNode.State.VALID):
			self.calculate()
		if(self._state == FNode.State.CALCULATED):
			if(isinstance(self._value, np.ndarray)):
				v = self._value
			elif(self._type < 10):
				v = self._value * np.ones((CURVE_FRAMES, CURVE_RESOLUTION))
			else:
				v = CALC_FUNCTIONS[self._type]
			return -v if self._negate else v
		return None
	

	def calculate(self):
		if(self._type >= FNode.Type.SET):
			return
		log.debug(f'{self} - calculating')
		
		calcFn = CALC_FUNCTIONS[self._type]

