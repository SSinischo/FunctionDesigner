from tkinter.font import names
from PyQt6.QtWidgets import *
from PyQt6.QtGui import *
from PyQt6.QtCore import *
from options import CURVE_FRAMES, CURVE_RESOLUTION
from stylesheets import *
from preview_plot import PreviewPlot
from fnode import FNode


class PreviewPanel(QFrame):
	activeNodeReplaced = pyqtSignal(object)
	
	def __init__(self, nodeView):
		super().__init__()
		self.activeNode = None
		self.nodeView = nodeView
		self.nodeView.itemSelectionChanged.connect(lambda *_: self.setActiveNode(self.nodeView.selectedNode()))
		self.activeNodeReplaced.connect(self.nodeView.replaceSelectedNode)
		self.setMouseTracking(True)

		self.previewFormula = QLineEdit()
		self.previewFormula.setFont(QFont('Consolas', 12))
		self.previewFormula.editingFinished.connect(self.onFormulaEdited)
		self.lastFormula = ''

		self.previewPlot = PreviewPlot()
		self.previewPlot.setMinimumWidth(600)
		self.previewPlot.setMinimumHeight(250)

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

		n = FNode.fromString(s)
		if(not n):
			return
		self.activeNodeReplaced.emit(n)

	
	def mouseMoveEvent(self, e):
		if(self.previewPlot.cursorPos):
			self.previewPlot.cursorPos = None
			self.previewPlot.update()
		return super().mouseMoveEvent(e)
