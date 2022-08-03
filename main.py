import sys
from PyQt6.QtWidgets import *
from PyQt6.QtGui import *
from PyQt6.QtCore import *
import numpy as np
from fnode import FNode
from node_view import NodeView

from options import CURVE_FRAMES, CURVE_RESOLUTION

class NodePalette(NodeView):
	def __init__(self):
		super().__init__()

		with open('default_palette.json') as f:
			s = ''.join(f.readlines())
			f.close()
		self.rootNode = FNode.fromString(s)
		self.defaultNodeIDs = set()
		self.isAddingDefaults = True
		self.createItems(self.rootNode)
		self.isAddingDefaults = False


	def dragMoveEvent(self, e):
		if(e.source() == self and self.isDefaultItem(self.selectedItem())):
			self.invisibleRootItem().setFlags(self.invisibleRootItem().flags() &  ~Qt.ItemFlag.ItemIsDropEnabled)
		else:
			self.invisibleRootItem().setFlags(self.invisibleRootItem().flags() | Qt.ItemFlag.ItemIsDropEnabled)
		return super().dragMoveEvent(e)


	def dragEnterEvent(self, e):
		return super().dragEnterEvent(e)
	

	def createItem(self, n):
		tItem = super().createItem(n)
		if(self.isAddingDefaults):
			tItem.setFlags(tItem.flags() &  ~Qt.ItemFlag.ItemIsDropEnabled)
			if(n.type() == FNode.Type.SET):
				tItem.setFlags(tItem.flags() &  ~Qt.ItemFlag.ItemIsDragEnabled)
			self.defaultNodeIDs.add(tItem.data(0, Qt.ItemDataRole.UserRole))
		return tItem


	def deleteSelectedItem(self):
		if(self.isDefaultItem(self.selectedItem())):
			return False
		return super().deleteSelectedItem()


	def isDefaultItem(self, tItem):
		return tItem and tItem.data(0, Qt.ItemDataRole.UserRole) in self.defaultNodeIDs


class CompositionView(NodeView):
	def __init__(self):
		super().__init__()


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


	def onSelectedNodeRefresh(self, n):
		if(not n):
			self.curve = PreviewPlot.DEFAULT_CURVE
		elif(not np.shape(n.value())):
			self.curve = n.value() * np.ones((CURVE_FRAMES, CURVE_RESOLUTION))
		else:
			self.curve = n.value()
		self.update()


	def onFrameIdxChanged(self, idx):
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


class PreviewFormula(QLineEdit):
	formulaUpdated = pyqtSignal(str)

	def __init__(self):
		super().__init__()
		self.setFont(QFont('Consolas', 12))
		self.editingFinished.connect(self.onEditingFinished)
		self.lastFormula = ''
	

	def onSelectedNodeRefresh(self, n):
		if(n):
			self.setText(n.formula())
			self.lastFormula = self.text()
		else:
			self.setText('')
			self.lastFormula = self.text()


	def onEditingFinished(self):
		s = self.text()
		if(s == self.lastFormula):
			return
		self.lastFormula = s
		self.formulaUpdated.emit(s)



class PreviewPanel(QFrame):
	def __init__(self):
		super().__init__()
		self.formula = PreviewFormula()
		self.plot = PreviewPlot()
		self.plot.setMinimumWidth(600)
		self.plot.setMinimumHeight(250)
		self.setMouseTracking(True)

		v = QVBoxLayout()
		v.addWidget(self.formula)
		v.addWidget(self.plot, 1)
		self.setLayout(v)

	
	def mouseMoveEvent(self, e):
		if(self.plot.cursorPos):
			self.plot.cursorPos = None
			self.plot.update()
		return super().mouseMoveEvent(e)



class Application(QApplication):
	def __init__(self, *args, **kwargs):
		super(Application, self).__init__(*args, **kwargs)

		self.previewPanel = PreviewPanel()
		self.nodePalette = NodePalette()
		self.compositionView = CompositionView()
		self.compositionView.selectedNodeRefresh.connect(self.previewPanel.formula.onSelectedNodeRefresh)
		self.compositionView.selectedNodeRefresh.connect(self.previewPanel.plot.onSelectedNodeRefresh)
		self.previewPanel.formula.formulaUpdated.connect(self.compositionView.onForumlaUpdated)

		self.sliderFrameIdx = QSlider(Qt.Orientation.Horizontal)
		self.sliderFrameIdx.setMaximum(CURVE_FRAMES-1)
		self.sliderFrameIdx.valueChanged.connect(self.onFrameIdxChanged)

		self.labelFrameIdx = QLabel('0', )
		self.labelFrameIdx.setFont(QFont('Consolas', 12))
		self.labelFrameIdx.setAlignment(Qt.AlignmentFlag.AlignCenter)

		self.labelZValue = QLabel('0.000')
		self.labelZValue.setFont(QFont('Consolas', 12))
		self.labelZValue.setAlignment(Qt.AlignmentFlag.AlignCenter)

		sliderContainer = QHBoxLayout()

		v = QVBoxLayout()
		l = QLabel('WT pos')
		l.setFont(QFont('Consolas', 8))
		v.addWidget(l)
		v.addWidget(self.labelFrameIdx)
		sliderContainer.addLayout(v)

		sliderContainer.addWidget(self.sliderFrameIdx, 1)

		v = QVBoxLayout()
		self.labelZLabel = QLabel('z')
		self.labelZLabel.setFont(QFont('Consolas', 8))
		self.labelZLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
		v.addWidget(self.labelZLabel)
		v.addWidget(self.labelZValue)
		sliderContainer.addLayout(v)

		v = QVBoxLayout()
		v.addWidget(self.previewPanel)
		v.addLayout(sliderContainer)

		h = QHBoxLayout()
		h.addWidget(self.nodePalette)
		h.addWidget(self.compositionView, 1)

		v.addLayout(h)

		f = QFrame()
		f.setLayout(v)
		self.mainWin = QMainWindow()
		self.mainWin.setCentralWidget(f)
		self.mainWin.setWindowTitle('Function Designer')
		self.mainWin.show()

		self.exec()
	
	def onFrameIdxChanged(self):
		self.previewPanel.plot.onFrameIdxChanged(self.sliderFrameIdx.value())
		self.labelFrameIdx.setText(str(self.sliderFrameIdx.value()))
		self.labelZValue.setText(f'{self.sliderFrameIdx.value()/self.sliderFrameIdx.maximum():0.3f}')


if __name__ == '__main__':
	Application(sys.argv)

	
	
