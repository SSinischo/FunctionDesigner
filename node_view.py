from PyQt6.QtWidgets import *
from PyQt6.QtGui import *
from PyQt6.QtCore import *
from fnode import FNode

class NodeView(QTreeWidget):
	selectedNodeRefresh = pyqtSignal(object)

	def __init__(self):
		super(QTreeWidget, self).__init__()
		self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
		self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
		self.setHeaderHidden(True)
		self.setDragDropMode(self.DragDropMode.DragDrop)
		self.setAcceptDrops(True)
		self.itemSelectionChanged.connect(lambda *_: self.selectedNodeRefresh.emit(self.selectedNode()))

		self.rootNode = FNode(FNode.Type.ROOT)
		self.attachNodeID(self.invisibleRootItem(), self.rootNode)
		self.lastDragged = None
		self.lastDraggedOver = None

	
	def selectedItem(self):
		tItems = self.selectedItems()
		return tItems[0] if tItems else None
	

	def attachNodeID(self, tItem, n):
		tItem.setData(0, Qt.ItemDataRole.UserRole, n.nodeID())
	

	def getAttachedNode(self, tItem):
		return FNode.getNode(tItem.data(0, Qt.ItemDataRole.UserRole)) if tItem else None
	

	def selectedNode(self):
		return self.getAttachedNode(self.selectedItem())


	def createItem(self, n):
		tItem = QTreeWidgetItem()
		self.attachNodeID(tItem, n)
		if(n.name()):
			tItem.setText(0, n.name())
		elif(n.type() == FNode.Type.CONSTANT):
			tItem.setText(0, n.formula())
			tItem.setFlags(tItem.flags() | Qt.ItemFlag.ItemIsEditable)
		else:
			tItem.setText(0, FNode.TYPE_NAMES[n.type()])

		if(n.isBaseNode()):
			tItem.setFlags(tItem.flags() ^  Qt.ItemFlag.ItemIsDropEnabled)
			if(n.type() == FNode.Type.SET):
				tItem.setFlags(tItem.flags() ^ Qt.ItemFlag.ItemIsDragEnabled)
		#n.nodeUpdated.connect(lambda n: self.selectedNodeRefresh.emit(n) if self.getAttachedNode(self.selectedItem()) == n else None)
		return tItem
	

	def createItems(self, rootNode, pItem=None):
		if(not pItem):
			pItem = self.invisibleRootItem()
		if(rootNode._type != FNode.Type.ROOT):
			tItem = self.createItem(rootNode)
			pItem.addChild(tItem)
		else:
			tItem = pItem
		for c in rootNode.children():
			self.createItems(c, tItem)
		#tItem.setExpanded(True)
		return tItem
	

	def deleteItemAndNodes(self, tItem, warnIfChildren=True):
		n = self.getAttachedNode(tItem)
		if(warnIfChildren and n.children()):
			msg = QMessageBox()
			msg.setText('The selected node is not a leaf.  Are you sure you want to delete the selected node and all of its children?')
			msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
			r = msg.exec()
			if(not r):
				return

		n.parent().deleteChild(n)
		pItem = tItem.parent() or self.invisibleRootItem()
		pItem.removeChild(tItem)

	
	def deleteSelectedItem(self):
		if(self.selectedNode().isBaseNode()):
			return False
		tItem = self.selectedItem()
		if(tItem):
			self.deleteItemAndNodes(tItem)
			return True
		return False
	

	def copySelectedItem(self):
		n = self.selectedNode()
		if(not n):
			return False
		QApplication.clipboard().setText(n.asString())
		return True
	

	def cutSelectedItem(self):
		if(self.copySelectedItem()):
			self.deleteItemAndNodes(self.selectedItem())
			return True
		return False


	def pasteFromClipboard(self):
		pItem = self.selectedItem() or self.invisibleRootItem()
		pn = self.getAttachedNode(pItem)
		n = FNode.fromString(QApplication.clipboard().text())
		if(n):
			pn.addChild(n)
			self.createItems(n, pItem)
			return True
		return False
	

	def onForumlaUpdated(self, s):
		try:
			nNew = FNode.fromString(s)
			assert nNew
			tItem = self.selectedItem()
			if(not tItem):
				self.invisibleRootItem().takeChildren()
				[self.rootNode.deleteChild(c) for c in self.rootNode.children()]
				pItem = self.invisibleRootItem()
				pn = self.rootNode
			else:
				pItem = tItem.parent() or self.invisibleRootItem()
				pItem.removeChild(tItem)
				n = self.getAttachedNode(tItem)
				pn = n.parent()
				pn.deleteChild(n)
			pn.addChild(nNew)
			tItem = self.createItems(nNew, pItem)
			tItem.setSelected(True)
			return True
		except Exception as e:
			#self.selectedNodeRefresh.emit(self.getAttachedNode(self.selectedItem()))
			return False


	def startDrag(self, supportedActions):
		self.lastDragged = self.selectedItem()
		return super().startDrag(supportedActions)


	def dropEvent(self, e: QDropEvent):
		if(not isinstance(e.source(), NodeView)):
			e.ignore()
			return

		if(e.source() != self):
			e.setDropAction(Qt.DropAction.CopyAction)
		else:
			e.setDropAction(Qt.DropAction.MoveAction)
	
		droppedNode = self.getAttachedNode(e.source().lastDragged)
		#pnOld = droppedNode.parent()
		epos = e.position().toPoint()
		tItemDroppedAt = self.itemAt(epos)
		idxDroppedAt = self.indexAt(epos)

		match(self.dropIndicatorPosition()):
			case self.DropIndicatorPosition.AboveItem:
				pItemNew = tItemDroppedAt.parent() or self.invisibleRootItem()
				cidx = idxDroppedAt.row()
			case self.DropIndicatorPosition.BelowItem:
				pItemNew = tItemDroppedAt.parent() or self.invisibleRootItem()
				cidx = idxDroppedAt.row() + 1
			case self.DropIndicatorPosition.OnItem:
				pItemNew = tItemDroppedAt
				#if(pnOld.parent() == self.getAttachedNode(pItemNew).parent()):
				if(droppedNode.parent() == self.getAttachedNode(pItemNew)):
					cidx = tItemDroppedAt.childCount() - 1
				else:
					cidx = tItemDroppedAt.childCount()
			case self.DropIndicatorPosition.OnViewport:
				pItemNew = self.invisibleRootItem()
				cidx = self.invisibleRootItem().childCount()

		super().dropEvent(e)
		tItem = pItemNew.child(cidx)

		pnNew = self.getAttachedNode(pItemNew)
		if(e.dropAction() == Qt.DropAction.CopyAction):
			droppedNode = droppedNode.copy()
			pnNew.addChild(droppedNode, cidx)
			if(droppedNode.children()):
				[self.createItems(c, tItem) for c in droppedNode.children()]
		else:
			#pnOld.removeChild(droppedNode)
			pnNew.addChild(droppedNode, cidx)

		self.attachNodeID(tItem, droppedNode)
		pItemNew.setExpanded(True)
		e.source().lastDragged = None


	def dragEnterEvent(self, e):
		if(not isinstance(e.source(), NodeView)):
			e.ignore()
			return
		return super().dragEnterEvent(e)


	def keyPressEvent(self, e):
		if(e.key() == Qt.Key.Key_Delete or e.key() == Qt.Key.Key_Backspace):
			self.deleteSelectedItem()
		elif(e.key() == Qt.Key.Key_C and e.modifiers() & Qt.KeyboardModifier.ControlModifier):
			self.copySelectedItem()
		elif(e.key() == Qt.Key.Key_X and e.modifiers() & Qt.KeyboardModifier.ControlModifier):
			self.cutSelectedItem()
		elif(e.key() == Qt.Key.Key_V and e.modifiers() & Qt.KeyboardModifier.ControlModifier):
			self.pasteFromClipboard()
		else:
			return super().keyPressEvent(e)
		