import sys
from PyQt6.QtWidgets import *
from PyQt6.QtGui import *
from PyQt6.QtCore import *
import numpy as np
from fnode import FNode, FNodeType
from node_view import NodeView
from preview_panel import PreviewPanel

from options import CURVE_FRAMES, CURVE_RESOLUTION
from stylesheets import *


class NodePalette(NodeView):
	def __init__(self, rootNode):
		super().__init__()
		self.rootNode = rootNode
		self.defaultNodeIDs = set()
		self.createTreeItems(self.rootNode)
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
			tItem = e.source().lastDraggedItem
			n = self.attachedNode(tItem)
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
		self.initDefineFunctionWindow()
		if(self.rootNode):
			self.createTreeItems(self.rootNode)
	

	def initDefineFunctionWindow(self):
		self.defineFnName = QLineEdit()
		self.defineFnOk = QPushButton('OK')
		self.defineFnCancel = QPushButton('Cancel')

		v = QVBoxLayout()
		h = QHBoxLayout()
		h.addWidget(QLabel("function name"))
		h.addWidget(self.defineFnName)
		v.addLayout(h)
		h = QHBoxLayout()
		h.addWidget(self.defineFnOk)
		h.addWidget(self.defineFnCancel)
		v.addLayout(h)
		self.defineFnWindow = QFrame()
		self.defineFnWindow.setLayout(v)
		self.defineFnCancel.clicked.connect(lambda *_: self.defineFnWindow.hide())
	

	def defineAsFunction(self, tItem: QTreeWidgetItem):
		n = self.attachedNode(tItem)
		fn = n.functionize()
		tItem.

	
	def contextMenuEvent(self, e: QContextMenuEvent) -> None:
		tItem = self.itemAt(e.pos())
		m = QMenu()
		aNewFolder = QAction('New Folder')
		aNewFn = QAction('Define as function...')
		aRename = QAction('Rename')
		aDelete = QAction('Delete')

		m.addAction(aNewFolder)
		if(tItem):
			n = self.attachedNode(tItem)
			if(n.type() == FNodeType.FUNCTION):
				m.addAction(aRename)
			else:
				m.addAction(aNewFn)
			m.addAction(aDelete)
		a = m.exec(self.mapToGlobal(e.pos()))
		if(a == aNewFn):
			self.defineFnOk.clicked.connect(lambda *_: self.defineAsFunction(tItem))
			self.defineFnWindow.show()

		return super().contextMenuEvent(e)
	

	def mousePressEvent(self, e: QMouseEvent) -> None:
		return super().mousePressEvent(e)



class CompositionPanel(QFrame):
	def __init__(self, defaultRootNode, userRootNode=None):
		super().__init__()
		self.nodePalette = NodePalette(defaultRootNode)
		self.userPalette = UserPalette(userRootNode)
		self.expTree = MainExpressionTree()

		self.quickButtons = {}
		for bLabel, tLabel in [('w', 'w'), ('x', 'x'), ('y', 'y'), ('z', 'z'), ('123', 'constant value'), ('var', 'function variable'), ('+', 'plus'), ('-', 'minus'), ('*', 'multiply'), ('÷', 'divide'), ('^', 'exponential')]:
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


	def keyPressEvent(self, e):
		if(e.key() == Qt.Key.Key_B and e.modifiers() & Qt.KeyboardModifier.ControlModifier):
			pass


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

		self.compositionPanel = CompositionPanel(defaultRootNode, userRootNode)
		self.previewPanel = PreviewPanel(self.compositionPanel.expTree)

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

	
	
