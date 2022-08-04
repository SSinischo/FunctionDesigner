import sys
from PyQt6.QtWidgets import *
from PyQt6.QtGui import *
from PyQt6.QtCore import *
import numpy as np
from fnode import FNode, FNodeType
from node_view import NodeView

from options import CURVE_FRAMES, CURVE_RESOLUTION
from stylesheets import *

class NodePalette(NodeView):
	def __init__(self, rootNode):
		super().__init__()
		self.rootNode = rootNode
		self.defaultNodeIDs = set()
		self.createItems(self.rootNode)
		self.invisibleRootItem().setFlags(self.invisibleRootItem().flags() &  ~Qt.ItemFlag.ItemIsDropEnabled)


	def dragEnterEvent(self, e):
		return e.ignore()
	

	def createItem(self, n):
		tItem = super().createItem(n)
		tItem.setFlags(tItem.flags() &  ~(Qt.ItemFlag.ItemIsDropEnabled | Qt.ItemFlag.ItemIsEditable))
		if(n.type() == FNodeType.SET):
			tItem.setFlags(tItem.flags() &  ~Qt.ItemFlag.ItemIsDragEnabled)
		self.defaultNodeIDs.add(tItem.data(0, Qt.ItemDataRole.UserRole))
		return tItem


	def deleteSelectedItem(self):
		return False


	def onQuickButtonPressed(self, b, tItem, e):
		prevSelection = self.selectedItem()
		prevTopItem = self.itemAt(0, 0)
		self.clearSelection()
		self.scrollToItem(tItem, QAbstractItemView.ScrollHint.EnsureVisible)
		p = self.visualItemRect(tItem).topLeft()
		mpe = QMouseEvent(QEvent.Type.MouseButtonPress, e.position()+QPointF(p), Qt.MouseButton.LeftButton, Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier)
		self.mousePressEvent(mpe)
		self.startDrag(Qt.DropAction.CopyAction)
		self.scrollToItem(prevTopItem, QAbstractItemView.ScrollHint.EnsureVisible)
		self.clearSelection()
		if(prevSelection):
			prevSelection.setSelected(True)


class MainExpressionTree(NodeView):
	def __init__(self):
		super().__init__()
		self.setStyleSheet(COMPOSITION_VIEW_STYLE)
	
	def dropEvent(self, e: QDropEvent):
		super().dropEvent(e)
		if(e.source() != self):
			tItem = e.source().lastDragged
			n = self.getAttachedNode(tItem)
			if(n.type() == FNodeType.CONSTANT):
				self.pauseItemUpdates = True
				tItem.setText(0, '0')
				self.pauseItemUpdates = False
				self.editItem(tItem, 0)


class UserPalette(NodeView):
	def __init__(self, rootNode):
		super().__init__()
		self.rootNode = rootNode
		self.defaultNodeIDs = set()
		self.isAddingDefaults = True
		if(self.rootNode):
			self.createItems(self.rootNode)


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



class PreviewPanel(QFrame):
	formulaUpdated = pyqtSignal(str)
	
	def __init__(self):
		super().__init__()
		self.activeNode = None

		self.previewFormula = QLineEdit()
		self.previewFormula.setFont(QFont('Consolas', 12))
		self.previewFormula.editingFinished.connect(self.onFormulaEdited)
		self.lastFormula = ''

		self.previewPlot = PreviewPlot()
		self.previewPlot.setMinimumWidth(600)
		self.previewPlot.setMinimumHeight(250)
		self.setMouseTracking(True)

		self.frameIdx = QSlider(Qt.Orientation.Horizontal)
		self.frameIdx.setMaximum(CURVE_FRAMES-1)
		self.frameIdx.valueChanged.connect(self.onFrameIdxChanged)

		self.labelFrameIdx = QLabel('0', )
		self.labelFrameIdx.setFont(QFont('Consolas', 12))
		self.labelFrameIdx.setAlignment(Qt.AlignmentFlag.AlignCenter)

		self.labelZValue = QLabel('0.000')
		self.labelZValue.setFont(QFont('Consolas', 12))
		self.labelZValue.setAlignment(Qt.AlignmentFlag.AlignCenter)

		h = QHBoxLayout()
		v = QVBoxLayout()
		l = QLabel('WT pos')
		l.setFont(QFont('Consolas', 8))
		v.addWidget(l)
		v.addWidget(self.labelFrameIdx)
		h.addLayout(v)

		h.addWidget(self.frameIdx, 1)

		v = QVBoxLayout()
		self.labelZLabel = QLabel('z')
		self.labelZLabel.setFont(QFont('Consolas', 8))
		self.labelZLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
		v.addWidget(self.labelZLabel)
		v.addWidget(self.labelZValue)
		h.addLayout(v)

		v = QVBoxLayout()
		v.addWidget(self.previewFormula)
		v.addWidget(self.previewPlot, 1)
		v.addLayout(h)
		self.setLayout(v)
	

	def setActiveNode(self, n):
		if(not n):
			self.previewPlot.setCurve(None)
			s = ''
		else:
			self.previewPlot.setCurve(n.value())
			s = n.formula()
		self.lastFormula = s
		self.previewFormula.setText(s)
	

	def onFrameIdxChanged(self, frameIdx):
		self.previewPlot.setFrame(self.frameIdx.value())
		self.labelFrameIdx.setText(str(self.frameIdx.value()))
		self.labelZValue.setText(f'{self.frameIdx.value()/self.frameIdx.maximum():0.3f}')


	def onFormulaEdited(self):
		s = self.previewFormula.text()
		if(s == self.lastFormula):
			return
		self.lastFormula = s
		self.formulaUpdated.emit(s)

	
	def mouseMoveEvent(self, e):
		if(self.previewPlot.cursorPos):
			self.previewPlot.cursorPos = None
			self.previewPlot.update()
		return super().mouseMoveEvent(e)


class CompositionPanel(QFrame):
	def __init__(self, defaultRootNode, userRootNode=None):
		super().__init__()
		self.nodePalette = NodePalette(defaultRootNode)
		self.userPalette = UserPalette(userRootNode)
		self.expTree = MainExpressionTree()

		self.quickButtons = {}
		for bLabel, tLabel in [('w', 'w'), ('x', 'x'), ('y', 'y'), ('z', 'z'), ('123', 'constant value'), ('+', 'plus'), ('-', 'minus'), ('*', 'multiply'), ('÷', 'divide'), ('^', 'exponential'), ('sin', 'sin')]:
			tItem = self.nodePalette.findItems(tLabel, Qt.MatchFlag.MatchExactly | Qt.MatchFlag.MatchRecursive, 0)[0]
			b = QPushButton(bLabel)
			b.setStyleSheet(QUICK_BUTTON_STYLE)
			b.mousePressEvent = lambda e, b=b, tItem=tItem: self.nodePalette.onQuickButtonPressed(b, tItem, e)
			self.quickButtons[bLabel] = b


		v = QVBoxLayout()

		h = QHBoxLayout()
		[h.addWidget(b) for b in self.quickButtons.values()]
		v.addLayout(h)

		h = QHBoxLayout()
		tabs = QTabWidget()
		tabs.addTab(self.nodePalette, 'Base Palette')
		tabs.addTab(self.userPalette, 'User Palette')
		h.addWidget(tabs)
		h.addWidget(self.expTree, 1)
		v.addLayout(h)

		self.setLayout(v)


class Application(QApplication):
	def __init__(self, *args, **kwargs):
		super(Application, self).__init__(*args, **kwargs)

		try:
			with open('default_palette.json') as f:
				s = ''.join(f.readlines())
				f.close()
			defaultRootNode = FNode.fromString(s)
			assert defaultRootNode
		except Exception as e:
			print('Failed to open default_palette.json!')
			exit(1)

		try:
			with open('user_palette.json') as f:
				s = ''.join(f.readlines())
				f.close()
			userRootNode = FNode.fromString(s)
			assert userRootNode
		except Exception as e:
			print('Failed to open user_palette.json!')
			userRootNode = None

		self.previewPanel = PreviewPanel()
		self.compositionPanel = CompositionPanel(defaultRootNode, userRootNode)
		self.previewPanel.formulaUpdated.connect(self.compositionPanel.expTree.onFormulaUpdated)
		self.compositionPanel.expTree.selectedNodeRefresh.connect(self.previewPanel.setActiveNode)

		v = QVBoxLayout()
		v.addWidget(self.previewPanel)
		v.addWidget(self.compositionPanel, 1)

		f = QFrame()
		f.setLayout(v)
		self.mainWin = QMainWindow()
		self.mainWin.setCentralWidget(f)
		self.mainWin.setWindowTitle('Function Designer')
		self.mainWin.setGeometry(0, 0, 600, 800)
		self.mainWin.show()

		self.previewPanel.previewFormula.setText('1+2*3*4+5+6')

		self.exec()

if __name__ == '__main__':
	Application(sys.argv)

	
	
