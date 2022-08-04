from enum import IntEnum
from tkinter import N
import numpy as np
from PyQt6.QtCore import QObject, pyqtSignal
from heapq import heappush, heappop
import json
import re
import gc

from options import CURVE_FRAMES, CURVE_RESOLUTION


class FNodeType(IntEnum):
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


class FNode(QObject):
	CALCULATED = 0
	UNCALCULATED = 1
	INVALID_CHILDREN = 2

	CALC_FUNCTIONS = {
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
	}


	STRING_FUNCTIONS = {
		FNodeType.PI: lambda *_: 'pi',
		FNodeType.E: lambda *_: 'e',
		FNodeType.W: lambda *_: 'w',
		FNodeType.X: lambda *_: 'x',
		FNodeType.Y: lambda *_: 'y',
		FNodeType.Z: lambda *_: 'z',
		FNodeType.SIN: lambda *c: f'sin({c[0]})',
		FNodeType.COS: lambda *c: f'cos({c[0]})',
		FNodeType.TAN: lambda *c: f'tan({c[0]})',
		FNodeType.ASIN: lambda *c: f'asin({c[0]})',
		FNodeType.ACOS: lambda *c: f'acos({c[0]})',
		FNodeType.ATAN: lambda *c: f'atan({c[0]})',
		FNodeType.SINH: lambda *c: f'sinh({c[0]})',
		FNodeType.COSH: lambda *c: f'cosh({c[0]})',
		FNodeType.TANH: lambda *c: f'tanh({c[0]})',
		FNodeType.ASINH: lambda *c: f'asinh({c[0]})',
		FNodeType.ACOSH: lambda *c: f'acosh({c[0]})',
		FNodeType.ATANH: lambda *c: f'atanh({c[0]})',
		FNodeType.LOG2: lambda *c: f'log2({c[0]})',
		FNodeType.LOG10: lambda *c: f'log10({c[0]})',
		FNodeType.LN: lambda *c: f'ln({c[0]})',
		FNodeType.SQRT: lambda *c: f'sqrt({c[0]})',
		FNodeType.SIGN: lambda *c: f'sign({c[0]})',
		FNodeType.RINT: lambda *c: f'rint({c[0]})',
		FNodeType.ABS: lambda *c: f'abs({c[0]})',
		FNodeType.NEGATE: lambda *c: f'-{c[0]}',
		FNodeType.ADD: lambda *c: '+'.join(c),
		FNodeType.SUBTRACT: lambda *c: '-'.join(c),
		FNodeType.MULTIPLY: lambda *c: '*'.join(c),
		FNodeType.DIVIDE: lambda *c: '/'.join(c),
		FNodeType.EXPONENT: lambda *c: '^'.join(c),
		FNodeType.EQUAL: lambda *c: '=='.join(c),
		FNodeType.NOT_EQUAL: lambda *c: '!='.join(c),
		FNodeType.LESS_THAN: lambda *c: '<'.join(c),
		FNodeType.LESS_EQ: lambda *c: '<='.join(c),
		FNodeType.GREATER_THAN: lambda *c: '>'.join(c),
		FNodeType.GREATER_EQ: lambda *c: '>='.join(c),
		FNodeType.OR: lambda *c: '||'.join(c),
		FNodeType.AND: lambda *c: '&&'.join(c),
		FNodeType.MIN: lambda *c: 'min(' + ','.join(c) + ')',
		FNodeType.MAX: lambda *c: 'max(' + ','.join(c) + ')',
		FNodeType.SUM: lambda *c: 'sum(' + ','.join(c) + ')',
		FNodeType.AVG: lambda *c: 'avg(' + ','.join(c) + ')',
	}


	PRIORITY = {
		FNodeType.NEGATE: 8,
		FNodeType.EXPONENT: 7,
		FNodeType.DIVIDE: 6,
		FNodeType.MULTIPLY: 6,
		FNodeType.SUBTRACT: 5,
		FNodeType.ADD: 5,
		FNodeType.LESS_THAN: 4,
		FNodeType.GREATER_THAN: 4,
		FNodeType.LESS_EQ: 4,
		FNodeType.GREATER_EQ: 4,
		FNodeType.EQUAL: 4,
		FNodeType.NOT_EQUAL: 4,
		FNodeType.OR: 2,
		FNodeType.AND: 1
	}


	TOKENS = {
		'||': FNodeType.OR,
		'z': FNodeType.Z,
		'y': FNodeType.Y,
		'x': FNodeType.X,
		'w': FNodeType.W,
		'tanh': FNodeType.TANH,
		'tan': FNodeType.TAN,
		'sum': FNodeType.SUM,
		'sqrt': FNodeType.SQRT,
		'sinh': FNodeType.SINH,
		'sin': FNodeType.SIN,
		'sign': FNodeType.SIGN,
		'rint': FNodeType.RINT,
		'pi': FNodeType.PI,
		'min': FNodeType.MIN,
		'max': FNodeType.MAX,
		'log2': FNodeType.LOG2,
		'log10': FNodeType.LOG10,
		'ln': FNodeType.LN,
		'e': FNodeType.E,
		'cosh': FNodeType.COSH,
		'cos': FNodeType.COS,
		'avg': FNodeType.AVG,
		'atanh': FNodeType.ATANH,
		'atan': FNodeType.ATAN,
		'asinh': FNodeType.ASINH,
		'asin': FNodeType.ASIN,
		'acosh': FNodeType.ACOSH,
		'acos': FNodeType.ACOS,
		'abs': FNodeType.ABS,
		'^': FNodeType.EXPONENT,
		'>=': FNodeType.GREATER_EQ,
		'>': FNodeType.GREATER_THAN,
		'==': FNodeType.EQUAL,
		'<=': FNodeType.LESS_EQ,
		'<': FNodeType.LESS_THAN,
		'/': FNodeType.DIVIDE,
		'-': FNodeType.SUBTRACT,
		'+': FNodeType.ADD,
		'*': FNodeType.MULTIPLY,
		')': FNodeType.CLOSE_PAREN,
		'(': FNodeType.OPEN_PAREN,
		'&&': FNodeType.AND,
		'!=': FNodeType.NOT_EQUAL
	}


	TYPE_NAMES = {
		FNodeType.CONSTANT: 'constant value',
		FNodeType.PI: 'pi',
		FNodeType.E: 'e',
		FNodeType.W: 'w',
		FNodeType.X: 'x',
		FNodeType.Y: 'y',
		FNodeType.Z: 'z',
		FNodeType.SIN: 'sin',
		FNodeType.COS: 'cos',
		FNodeType.TAN: 'tan',
		FNodeType.ASIN: 'arcsin',
		FNodeType.ACOS: 'arccos',
		FNodeType.ATAN: 'arctan',
		FNodeType.SINH: 'sinh',
		FNodeType.COSH: 'cosh',
		FNodeType.TANH: 'tanh',
		FNodeType.ASINH: 'asinh',
		FNodeType.ACOSH: 'acosh',
		FNodeType.ATANH: 'atanh',
		FNodeType.LOG2: 'log (base 2)',
		FNodeType.LOG10: 'log (base 10)',
		FNodeType.LN: 'log (base e)',
		FNodeType.SQRT: 'square root',
		FNodeType.SIGN: 'sign',
		FNodeType.RINT: 'round',
		FNodeType.ABS: 'absolute value',
		FNodeType.NEGATE: 'negate',
		FNodeType.ADD: 'plus',
		FNodeType.SUBTRACT: 'minus',
		FNodeType.MULTIPLY: 'multiply',
		FNodeType.DIVIDE: 'divide',
		FNodeType.EXPONENT: 'exponential',
		FNodeType.EQUAL: 'equals',
		FNodeType.NOT_EQUAL: 'not equals',
		FNodeType.LESS_THAN: 'less than',
		FNodeType.LESS_EQ: 'less or eq.',
		FNodeType.GREATER_THAN: 'greater than',
		FNodeType.GREATER_EQ: 'greater or eq.',
		FNodeType.OR: 'or',
		FNodeType.AND: 'and',
		FNodeType.MIN: 'minimum',
		FNodeType.MAX: 'maximum',
		FNodeType.SUM: 'sum',
		FNodeType.AVG: 'average'
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
		return f'{self._name if self._name else self._value if self._type == FNodeType.CONSTANT else ""} {self._type.name} #{self._nodeID} C{len(self._children)}'
	

	def __str__(self):
		return f'{self._name+" " if self._name else (str(self._value)+" " if self._type == FNodeType.CONSTANT else "")}{self._type.name} #{self._nodeID} ({len(self._children)})'


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
		assert self._type == FNodeType.CONSTANT
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
		
		if(self._type == FNodeType.ROOT or self._type == FNodeType.SET):
			return

		if(not self.hasValidChildren()):
			print(f'{self} - invalid child count!')
			return self.invalidate(calcParent)

		if(self._type != FNodeType.CONSTANT):
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


	def addChild(self, child, idx=None):
		print(f'{self} - adding {child}')
		if(idx == None):
			idx = len(self._children)
		if(child._parent):
			child._parent.removeChild(child)
		if(child._type == self._type):
			for c in child._children:
				c._parent = self
			self._children = self._children[:idx] + child._children + self._children[idx:]
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
		if(self._type == FNodeType.CONSTANT):
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
	def tokenToNode(_, t:str, prevToken:str=None) -> "FNode":
		nType = FNode.TOKENS.get(t)
		if(not nType):
			try:
				f = float(t)
			except:
				print('Invalid token!')
				return
			n = FNode(FNodeType.CONSTANT)
			n.setConstantValue(f)
			return n
		if(nType == FNodeType.SUBTRACT):
			if(not prevToken or FNode.PRIORITY.get(FNode.TOKENS.get(prevToken)) or prevToken == '('):
				nType = FNodeType.NEGATE
		return FNode(nType)


	@classmethod
	def fromFormula(_, infixStr:str) -> "FNode":
		rexp = r'([a-z]+|[0-9.]+|==|>=|<=|&&|!=|\|\||[\(\)\^\/*\-+])'
		tokens = re.findall(rexp, infixStr.lower())
		outputQ = []
		opStack = []

		def addToOutput(n):
			if(n.isUnary()):
				return outputQ.append(n)
			rChild = outputQ.pop()
			if(n.isFunction()):
				n.addChild(rChild)
				return outputQ.append(n)
			if(n._type == FNodeType.NEGATE):
				rChild.negate()
				return outputQ.append(rChild)
			lChild = outputQ.pop()
			n.addChild(lChild)
			n.addChild(rChild)
			outputQ.append(n)


		for i, t in enumerate(tokens):
			n = FNode.tokenToNode(t, None if i==0 else tokens[i-1])

			if(n.isUnary()):
				addToOutput(n)
			elif(t == '(' or n.isFunction()):
				opStack.append(n)
			elif(n.isOperator() or n._type == FNodeType.NEGATE):
				while(opStack and opStack[-1]._type != FNodeType.OPEN_PAREN and opStack[-1].priority() >= n.priority()):
					addToOutput(opStack.pop())
				opStack.append(n)
			elif(t == ')'):
				try:
					while(True):
						nOp = opStack.pop()
						if(nOp._type == FNodeType.OPEN_PAREN):
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
		n = FNode(FNodeType(j['type']))
		n._name = j.get('name')
		if(n._type == FNodeType.CONSTANT):
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