
from PyQt6.QtWidgets import *
from PyQt6.QtGui import *
from PyQt6.QtCore import *
import numpy as np
from options import CURVE_FRAMES, CURVE_RESOLUTION
from stylesheets import *


class PreviewPlot(QWidget):
	DEFAULT_CURVE = np.zeros((CURVE_FRAMES, CURVE_RESOLUTION))

	def __init__(self):
		super().__init__()
		self.setStyleSheet("background-color: black;")
		self.setMouseTracking(True)
		self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
		self.curve = PreviewPlot.DEFAULT_CURVE
		self.renderedFrame = np.zeros((2, CURVE_RESOLUTION))
		self.frame = 0
		self.cursorPos = None
		self.showAltInfo = False
	

	def setCurve(self, curve):
		if(curve is None):
			self.curve = PreviewPlot.DEFAULT_CURVE
		elif(not np.shape(curve)):
			self.curve = curve * np.ones((CURVE_FRAMES, CURVE_RESOLUTION))
		else:
			self.curve = curve
		self.update()


	def setFrame(self, idx):
		self.frame = idx
		self.update()
	

	def keyPressEvent(self, e: QKeyEvent) -> None:
		self.showAltInfo = e.modifiers() & Qt.KeyboardModifier.ShiftModifier
		self.update()
		return super().keyPressEvent(e)


	def keyReleaseEvent(self, e: QKeyEvent) -> None:
		if(self.showAltInfo):
			self.showAltInfo = False
			self.update()
		return super().keyReleaseEvent(e)


	def mouseMoveEvent(self, e: QMouseEvent):
		self.cursorPos = e.position().toPoint()
		self.update()
	

	def paintEvent(self, e):
		h = self.height() / 2.0
		frame = (self.curve[self.frame].clip(-1, 1) * -h + h).astype('int')
		xVals = np.linspace(0, self.width(), len(frame), dtype='int')
		self.renderedFrame = np.array((xVals, frame))
		points = [QPoint(xVals[i], frame[i]) for i in range(len(frame))]
		p = QPainter(self)
		p.setRenderHint(QPainter.RenderHint.Antialiasing)
		p.fillRect(0, 0, self.width(), self.height(), Qt.GlobalColor.black)
		p.setPen(QPen(Qt.GlobalColor.green, 2, Qt.PenStyle.SolidLine))
		p.drawPolyline(points)
		
		if(self.cursorPos):
			cX, cY = (self.cursorPos.x(), self.cursorPos.y())
			i = np.searchsorted(self.renderedFrame[0], cX)
			curveY = self.renderedFrame[1][i]

			p.setPen(QPen(Qt.GlobalColor.gray, 1, Qt.PenStyle.SolidLine))
			p.drawLine(cX, 0, cX, self.height())
			p.drawLine(0, curveY, self.width(), curveY)

			popupRect = QRect(cX-80, cY-40, 80, 40)
			if(popupRect.left() < 0):
				popupRect.moveLeft(cX)
			if(popupRect.top() < 0):
				popupRect.moveTop(cY)

			p.fillRect(popupRect, QColor(209, 212, 180))
			p.setPen(QPen(Qt.GlobalColor.black, 2, Qt.PenStyle.SolidLine))

			if(self.showAltInfo):
				s1 = f'{2*(i/len(frame))-1:0.4f}'
			else:
				s1 = f'{i/len(frame):0.4f}'
			s2 = f'{self.curve[self.frame][i]:0.4f}'
			rect = QRect(popupRect.left()+3, popupRect.top()+3, popupRect.width()-6, 15)
			p.setFont(QFont('Consolas', 8))
			p.drawText(rect.adjusted(0, 3, -63, 3), Qt.AlignmentFlag.AlignRight, 'w' if self.showAltInfo else 'x')
			p.drawText(rect.adjusted(0, 18, -63, 18), Qt.AlignmentFlag.AlignRight, 'fx')
			p.setFont(QFont('Consolas', 12))
			p.drawText(rect, Qt.AlignmentFlag.AlignRight, s1)
			p.drawText(rect.adjusted(0, 15, 0, 15), Qt.AlignmentFlag.AlignRight, s2)
		p.end()

