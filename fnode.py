from enum import IntEnum
from tkinter import N
import numpy as np
from PyQt6.QtCore import QObject, pyqtSignal
from heapq import heappush, heappop
import json
import re
import gc

from options import CURVE_FRAMES, CURVE_RESOLUTION

class FNode(QObject):
	CALCULATED = 0
	UNCALCULATED = 1
	INVALID_CHILDREN = 2


	class Type(IntEnum):
		CONSTANT = 0
		W = 10
		X = 11
		Y = 12
		Z = 13
		PI = 50
		E = 51
		ADD = 100
		SUBTRACT = 101
		MULTIPLY = 102
		DIVIDE = 103
		EXPONENT = 104
		EQUAL = 105
		NOT_EQUAL = 106
		LESS_THAN = 107
		LESS_EQ = 108
		GREATER_THAN = 109
		GREATER_EQ = 110
		OR = 111
		AND = 112
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
		LOG2 = 300
		LOG10 = 301
		LN = 302
		SQRT = 303
		SIGN = 304
		RINT = 305
		ABS = 306
		MIN = 350
		MAX = 351
		SUM = 352
		AVG = 353
		NEGATE = 400
		OPEN_PAREN = 500
		CLOSE_PAREN = 501
		VARIABLE = 600
		SET = 700
		FUNCTION = 800
		ROOT = 999
	

	CALC_FUNCTIONS = {
		Type.PI: lambda *_: np.pi,
		Type.E: lambda *_: np.e,
		Type.W: lambda *_: np.tile(np.linspace(0, 1, CURVE_RESOLUTION), (CURVE_FRAMES, 1)),
		Type.X: lambda *_: np.tile(np.linspace(-1, 1, CURVE_RESOLUTION), (CURVE_FRAMES, 1)),
		Type.Y: lambda *_: np.repeat(np.linspace(-1, 1, CURVE_FRAMES), CURVE_RESOLUTION).reshape(CURVE_FRAMES, CURVE_RESOLUTION),
		Type.Z: lambda *_: np.repeat(np.linspace(0, 1, CURVE_FRAMES), CURVE_RESOLUTION).reshape(CURVE_FRAMES, CURVE_RESOLUTION),
		Type.SIN: np.sin,
		Type.COS: np.cos,
		Type.TAN: np.tan,
		Type.ASIN: np.arcsin,
		Type.ACOS: np.arccos,
		Type.ATAN: np.arctan,
		Type.SINH: np.sinh,
		Type.COSH: np.cosh,
		Type.TANH: np.tanh,
		Type.ASINH: np.arcsinh,
		Type.ACOSH: np.arccosh,
		Type.ATANH: np.arctanh,
		Type.LOG2: np.log2,
		Type.LOG10: np.log10,
		Type.LN: np.log,
		Type.SQRT: np.sqrt,
		Type.SIGN: np.sign,
		Type.RINT: np.rint,
		Type.ABS: np.abs,
		Type.NEGATE: np.negative,
		Type.ADD: lambda *c: FNode.accumulate(np.add, c),
		Type.SUBTRACT: lambda *c: FNode.accumulate(np.subtract, c),
		Type.MULTIPLY: lambda *c: FNode.accumulate(np.multiply, c),
		Type.DIVIDE: lambda *c: FNode.accumulate(np.divide, c),
		Type.EXPONENT: lambda *c: FNode.accumulate(np.power, c),
		Type.EQUAL: lambda *c: FNode.accumulate(lambda x, y: np.equal(x, y).astype(int), c),
		Type.NOT_EQUAL: lambda *c: 106,
		Type.LESS_THAN: lambda *c: 107,
		Type.LESS_EQ: lambda *c: 108,
		Type.GREATER_THAN: lambda *c: 109,
		Type.GREATER_EQ: lambda *c: 110,
		Type.OR: lambda *c: 111,
		Type.AND: lambda *c: 112,
		Type.MIN: lambda *c: 113,
		Type.MAX: lambda *c: 114,
		Type.SUM: lambda *c: 115,
		Type.AVG: lambda *c: 116
	}


	STRING_FUNCTIONS = {
		Type.PI: lambda *_: 'pi',
		Type.E: lambda *_: 'e',
		Type.W: lambda *_: 'w',
		Type.X: lambda *_: 'x',
		Type.Y: lambda *_: 'y',
		Type.Z: lambda *_: 'z',
		Type.SIN: lambda *c: f'sin({c[0]})',
		Type.COS: lambda *c: f'cos({c[0]})',
		Type.TAN: lambda *c: f'tan({c[0]})',
		Type.ASIN: lambda *c: f'asin({c[0]})',
		Type.ACOS: lambda *c: f'acos({c[0]})',
		Type.ATAN: lambda *c: f'atan({c[0]})',
		Type.SINH: lambda *c: f'sinh({c[0]})',
		Type.COSH: lambda *c: f'cosh({c[0]})',
		Type.TANH: lambda *c: f'tanh({c[0]})',
		Type.ASINH: lambda *c: f'asinh({c[0]})',
		Type.ACOSH: lambda *c: f'acosh({c[0]})',
		Type.ATANH: lambda *c: f'atanh({c[0]})',
		Type.LOG2: lambda *c: f'log2({c[0]})',
		Type.LOG10: lambda *c: f'log10({c[0]})',
		Type.LN: lambda *c: f'ln({c[0]})',
		Type.SQRT: lambda *c: f'sqrt({c[0]})',
		Type.SIGN: lambda *c: f'sign({c[0]})',
		Type.RINT: lambda *c: f'rint({c[0]})',
		Type.ABS: lambda *c: f'abs({c[0]})',
		Type.NEGATE: lambda *c: f'-{c[0]}',
		Type.ADD: lambda *c: '+'.join(c),
		Type.SUBTRACT: lambda *c: '-'.join(c),
		Type.MULTIPLY: lambda *c: '*'.join(c),
		Type.DIVIDE: lambda *c: '/'.join(c),
		Type.EXPONENT: lambda *c: '^'.join(c),
		Type.EQUAL: lambda *c: '=='.join(c),
		Type.NOT_EQUAL: lambda *c: '!='.join(c),
		Type.LESS_THAN: lambda *c: '<'.join(c),
		Type.LESS_EQ: lambda *c: '<='.join(c),
		Type.GREATER_THAN: lambda *c: '>'.join(c),
		Type.GREATER_EQ: lambda *c: '>='.join(c),
		Type.OR: lambda *c: '||'.join(c),
		Type.AND: lambda *c: '&&'.join(c),
		Type.MIN: lambda *c: 'min(' + ','.join(c) + ')',
		Type.MAX: lambda *c: 'max(' + ','.join(c) + ')',
		Type.SUM: lambda *c: 'sum(' + ','.join(c) + ')',
		Type.AVG: lambda *c: 'avg(' + ','.join(c) + ')',
	}


	PRIORITY = {
		Type.NEGATE: 8,
		Type.EXPONENT: 7,
		Type.DIVIDE: 6,
		Type.MULTIPLY: 6,
		Type.SUBTRACT: 5,
		Type.ADD: 5,
		Type.LESS_THAN: 4,
		Type.GREATER_THAN: 4,
		Type.LESS_EQ: 4,
		Type.GREATER_EQ: 4,
		Type.EQUAL: 4,
		Type.NOT_EQUAL: 4,
		Type.OR: 2,
		Type.AND: 1
	}


	TOKENS = {
		'||': Type.OR,
		'z': Type.Z,
		'y': Type.Y,
		'x': Type.X,
		'w': Type.W,
		'tanh': Type.TANH,
		'tan': Type.TAN,
		'sum': Type.SUM,
		'sqrt': Type.SQRT,
		'sinh': Type.SINH,
		'sin': Type.SIN,
		'sign': Type.SIGN,
		'rint': Type.RINT,
		'pi': Type.PI,
		'min': Type.MIN,
		'max': Type.MAX,
		'log2': Type.LOG2,
		'log10': Type.LOG10,
		'ln': Type.LN,
		'e': Type.E,
		'cosh': Type.COSH,
		'cos': Type.COS,
		'avg': Type.AVG,
		'atanh': Type.ATANH,
		'atan': Type.ATAN,
		'asinh': Type.ASINH,
		'asin': Type.ASIN,
		'acosh': Type.ACOSH,
		'acos': Type.ACOS,
		'abs': Type.ABS,
		'^': Type.EXPONENT,
		'>=': Type.GREATER_EQ,
		'>': Type.GREATER_THAN,
		'==': Type.EQUAL,
		'<=': Type.LESS_EQ,
		'<': Type.LESS_THAN,
		'/': Type.DIVIDE,
		'-': Type.SUBTRACT,
		'+': Type.ADD,
		'*': Type.MULTIPLY,
		')': Type.CLOSE_PAREN,
		'(': Type.OPEN_PAREN,
		'&&': Type.AND,
		'!=': Type.NOT_EQUAL
	}


	TYPE_NAMES = {
		Type.CONSTANT: 'constant value',
		Type.PI: 'pi',
		Type.E: 'e',
		Type.W: 'w',
		Type.X: 'x',
		Type.Y: 'y',
		Type.Z: 'z',
		Type.SIN: 'sin',
		Type.COS: 'cos',
		Type.TAN: 'tan',
		Type.ASIN: 'arcsin',
		Type.ACOS: 'arccos',
		Type.ATAN: 'arctan',
		Type.SINH: 'sinh',
		Type.COSH: 'cosh',
		Type.TANH: 'tanh',
		Type.ASINH: 'asinh',
		Type.ACOSH: 'acosh',
		Type.ATANH: 'atanh',
		Type.LOG2: 'log (base 2)',
		Type.LOG10: 'log (base 10)',
		Type.LN: 'log (base e)',
		Type.SQRT: 'square root',
		Type.SIGN: 'sign',
		Type.RINT: 'round',
		Type.ABS: 'absolute value',
		Type.NEGATE: 'negate',
		Type.ADD: 'plus',
		Type.SUBTRACT: 'minus',
		Type.MULTIPLY: 'multiply',
		Type.DIVIDE: 'divide',
		Type.EXPONENT: 'exponentiate',
		Type.EQUAL: 'equals',
		Type.NOT_EQUAL: 'not equals',
		Type.LESS_THAN: 'less than',
		Type.LESS_EQ: 'less or eq.',
		Type.GREATER_THAN: 'greater than',
		Type.GREATER_EQ: 'greater or eq.',
		Type.OR: 'or',
		Type.AND: 'and',
		Type.MIN: 'minimum',
		Type.MAX: 'maximum',
		Type.SUM: 'sum',
		Type.AVG: 'average'
	}


	ID_COUNTER = 0
	ACTIVE_NODES = {}
	PAUSE_CALCULATIONS = False

	nodeUpdated = pyqtSignal(object)

	def __init__(self, type:int):
		super().__init__()
		self._nodeID = FNode.ID_COUNTER
		FNode.ID_COUNTER += 1
		FNode.ACTIVE_NODES[self._nodeID] = self
		self._type = type
		self._parent = None
		self._children = []
		self._negated = False
		self._name = None
		self._value = 0
		self._formula = ''
		self.state = FNode.UNCALCULATED
		
		print(f'{self} - created')


	def __repr__(self) -> str:
		return f'{self._name if self._name else self._value if self._type == FNode.Type.CONSTANT else ""} {self._type.name} #{self._nodeID} C{len(self._children)}'
	

	def __str__(self):
		return f'{self._name+" " if self._name else (str(self._value)+" " if self._type == FNode.Type.CONSTANT else "")}{self._type.name} #{self._nodeID} ({len(self._children)})'


	def nodeID(self):
		return self._nodeID

	def type(self):
		return self._type

	def setType(self, t):
		self._type = t
		self.calculate()

	def name(self):
		return self._name

	def setName(self, name):
		self._name = name
	
	def parent(self):
		return self._parent
	
	def children(self):
		return self._children

	def value(self):
		return self._value

	def formula(self):
		return self._formula
	
	def isNegated(self):
		return self._negated

	def isUnary(self):
		return self._type < 100

	def isOperator(self):
		return 100 <= self._type <= 112

	def isFunction(self):
		return 200 <= self._type < 400
	
	def priority(self):
		return FNode.PRIORITY.get(self._type)

	def negate(self):
		self._negated = not self._negated
		self.calculate()


	def setConstantValue(self, value):
		assert self._type == FNode.Type.CONSTANT
		self._negated = value < 0
		self._value = -value if self._negated else value
		self._formula = str(int(self._value) if not self._value % 1 else self._value)
		self.calculate()


	def childLimit(self):
		return 0 if self._type < 40 else 1 if self._type < 100 else float('inf')


	def hasValidChildren(self):
		if(self.isUnary()):
			return len(self._children) == 0
		if(self.isFunction()):
			return len(self._children) == 1
		return len(self._children) > 0
	

	def invalidate(self, invalidateParent=True):
		self.state = FNode.INVALID_CHILDREN
		if(invalidateParent and self._parent):
			self._parent.invalidate()


	def calculate(self, calcParent=True):
		if(FNode.PAUSE_CALCULATIONS):
			return

		print(f'{self} - calculating')

		for c in self._children:
			if(c.state == FNode.UNCALCULATED):
				print(f'{self} - uncalculated children!')
				c.calculate(False)
			if(c.state == FNode.INVALID_CHILDREN):
				return self.invalidate(calcParent)
		
		if(self._type == FNode.Type.ROOT or self._type == FNode.Type.SET):
			return

		if(not self.hasValidChildren()):
			print(f'{self} - invalid child count!')
			return self.invalidate(calcParent)

		if(self._type != FNode.Type.CONSTANT):
			calcFn = FNode.CALC_FUNCTIONS[self._type]
			strFn = FNode.STRING_FUNCTIONS[self._type]
			self._value = calcFn(*[c._value for c in self._children])
			pSelf = FNode.PRIORITY.get(self._type)
			if(pSelf):
				cStrsParens = []
				for c in self._children:
					pC = FNode.PRIORITY.get(c._type)
					if(pC and pSelf > pC):
						cStrsParens.append(f'({c._formula})')
					else:
						cStrsParens.append(c._formula)
				self._formula = strFn(*cStrsParens)
			else:
				self._formula = strFn(*[c._formula for c in self._children])

		if(self._negated):
			self._value *= -1
			if(len(self._children) > 1):
				self._formula = f'-({self._formula})'
			else:
				self._formula = f'-{self._formula}'

		self.state = FNode.CALCULATED
		self.nodeUpdated.emit(self)
		if(calcParent and self._parent):
			self._parent.calculate()


	def addChild(self, child, idx=-1):
		print(f'{self} - adding {child}')
		if(child._parent):
			child._parent.removeChild(child)
		if(child._type == self._type):
			for c in child._children:
				c._parent = self
			if(idx > 0):
				self._children = self._children[:idx] + child._children + self._children[idx:]
			else:
				self._children = child._children + self._children
		else:
			child._parent = self
			self._children.insert(idx, child)
		self.calculate()


	def removeChild(self, child):
		print(f'{self} - removing {child}')
		child._parent = None
		self._children.remove(child)
		self.calculate()
	

	def deleteChild(self, child):
		print(f'{self} - deleting {child}')
		def recurse(n):
			FNode.ACTIVE_NODES.pop(n._nodeID)
			[recurse(c) for c in n._children]
			try:
				n.nodeUpdated.disconnect()
			except:
				pass
			del n
		self.removeChild(child)
		recurse(child)
		gc.collect()


	def asJSON(self):
		j = {'type': int(self._type)}
		if(self._name):
			j['name'] = self._name
		if(self._type == FNode.Type.CONSTANT):
			j['value'] = int(self._value) if not self._value % 1 else self._value
		if(self._children):
			j['children'] = [c.asJSON() for c in self._children]
		return j


	def asString(self):
		# if(self.state == FNode.CALCULATED):
		# 	return self._formula
		# else:
			return json.dumps(self.asJSON())
	

	def copy(self):
		n = FNode.fromJSON(self.asJSON())
		return n
	

	@classmethod
	def tokenToNode(_, t, prevToken=None):
		nType = FNode.TOKENS.get(t)
		if(not nType):
			try:
				f = float(t)
			except:
				print('Invalid token!')
				return
			n = FNode(FNode.Type.CONSTANT)
			n.setConstantValue(f)
			return n
		if(nType == FNode.Type.SUBTRACT):
			if(not prevToken or FNode.PRIORITY.get(prevToken) or prevToken == '('):
				nType = FNode.Type.NEGATE
		return FNode(nType)
	

	@classmethod
	def fromFormula(_, s):
		rexp = r'([a-z]+|[0-9.]+|==|>=|<=|&&|!=|\|\||[\(\)\^\/*\-+])'
		tokens = re.findall(rexp, s.lower())
		outputQ = []
		opStack = []

		def addToOutput(n):
			if(n.isUnary()):
				return outputQ.append(n)
			rChild = outputQ.pop()
			if(n.isFunction()):
				n.addChild(rChild)
				return outputQ.append(n)
			if(n._type == FNode.Type.NEGATE):
				rChild.negate()
				return outputQ.append(rChild)
			lChild = outputQ.pop()
			n.addChild(rChild)
			n.addChild(lChild)
			outputQ.append(n)


		for i, t in enumerate(tokens):
			n = FNode.tokenToNode(t, None if i==0 else tokens[i-1])

			if(n.isUnary()):
				addToOutput(n)
			elif(t == '(' or n.isFunction()):
				opStack.append(n)
			elif(n.isOperator() or n._type == FNode.Type.NEGATE):
				while(opStack and opStack[-1]._type != FNode.Type.OPEN_PAREN and opStack[-1].priority() >= n.priority()):
					addToOutput(opStack.pop())
				opStack.append(n)
			elif(t == ')'):
				try:
					while(True):
						nOp = opStack.pop()
						if(nOp._type == FNode.Type.OPEN_PAREN):
							break
						addToOutput(nOp)
				except Exception as e:
					print('Closing parenthesis does not match any opening parenthesis!')
					return
				if(opStack and opStack[-1].isFunction()):
					addToOutput(opStack.pop())
		while(opStack):
			addToOutput(opStack.pop())

		return outputQ.pop()


	@classmethod
	def fromJSON(_, j):
		n = FNode(FNode.Type(j['type']))
		n._name = j.get('name')
		if(n._type == FNode.Type.CONSTANT):
			n.setConstantValue(j.get('value') or 0)
		for c in j.get('children') or []:
			n.addChild(FNode.fromJSON(c))
		return n


	@classmethod
	def fromString(_, s):
		FNode.PAUSE_CALCULATIONS = True
		try:
			j = json.loads(s)
			n = FNode.fromJSON(j)
		except Exception as e:
			n = FNode.fromFormula(s)
		FNode.PAUSE_CALCULATIONS = False
		if(n):
			n.calculate()
		return n

	@classmethod
	def accumulate(_, fn, params):
		if(not params):
			return 0
		s = params[0]
		for i in range(1, len(params)):
			s = fn(s, params[i])
		return s


	@classmethod
	def pauseCalculations(_):
		if(not FNode.PAUSE_CALCULATIONS):
			print('Pausing calculations')
			FNode.PAUSE_CALCULATIONS = True

	@classmethod
	def unpauseCalculations(_):
		if(FNode.PAUSE_CALCULATIONS):
			print('Unpausing calculations')
			FNode.PAUSE_CALCULATIONS = False

	@classmethod
	def getNode(_, nodeID):
		return FNode.ACTIVE_NODES.get(nodeID)

#n = FNode.fromString('2^3+5*20')
#n = FNode.fromFormula('2^3+sin(x+5)*(20-6)*4')
#s = n.asString()
#n2 = FNode.fromString(s)
#print(n2._formula)
pass