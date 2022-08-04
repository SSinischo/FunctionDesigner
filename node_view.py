from PyQt6.QtWidgets import *
from PyQt6.QtGui import *
from PyQt6.QtCore import *
from fnode import FNode, FNodeType

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
		self.itemChanged.connect(lambda *x: self.onItemUpdated(x))

		self.rootNode = FNode(FNodeType.ROOT)
		self.attachNodeID(self.invisibleRootItem(), self.rootNode)
		self.lastDragged = None
		self.lastDraggedOver = None
		self.pauseItemUpdates = False

	
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
		elif(n.type() == FNodeType.CONSTANT):
			self.pauseItemUpdates = True
			tItem.setText(0, n.formula())
			self.pauseItemUpdates = False
		else:
			tItem.setText(0, FNode.TYPE_NAMES[n.type()])
		if(n.type() == FNodeType.CONSTANT):
			tItem.setFlags(tItem.flags() | Qt.ItemFlag.ItemIsEditable)
		#n.nodeUpdated.connect(lambda n: self.selectedNodeRefresh.emit(n) if self.getAttachedNode(self.selectedItem()) == n else None)
		return tItem
	

	def createItems(self, rootNode, pItem=None, idx=None):
		if(pItem == None):
			pItem = self.invisibleRootItem()
		if(idx == None):
			idx = pItem.childCount()
		if(rootNode._type != FNodeType.ROOT):
			tItem = self.createItem(rootNode)
			pItem.insertChild(idx, tItem)
		else:
			tItem = pItem
		for c in rootNode.children():
			self.createItems(c, tItem)
		tItem.setExpanded(True)
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


	def onItemUpdated(self, itemUpdated):
		if(self.pauseItemUpdates):
			return
		n = self.getAttachedNode(itemUpdated[0])
		if(not n or n.type() != FNodeType.CONSTANT):
			return
		try:
			n.setConstantValue(float(itemUpdated[0].text(0)))
		except:
			itemUpdated[0].setText(0, '0')
	

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
				idx = None
			else:
				pItem = tItem.parent() or self.invisibleRootItem()
				idx = pItem.indexOfChild(tItem)
				pItem.removeChild(tItem)
				n = self.getAttachedNode(tItem)
				pn = n.parent()
				pn.deleteChild(n)
			pn.addChild(nNew, idx)
			tItem = self.createItems(nNew, pItem, idx)
			self.clearSelection()
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
	
		sourceItemDragged = e.source().selectedItem()
		sourcePItemDragged = sourceItemDragged.parent() or self.invisibleRootItem()
		ePos = e.position().toPoint()
		tItemDroppedAt = self.itemAt(ePos)
		qmidxDroppedAt = self.indexAt(ePos)

		match(self.dropIndicatorPosition()):
			case self.DropIndicatorPosition.AboveItem:
				pItemDroppedAt = tItemDroppedAt.parent() or self.invisibleRootItem()
				idxDroppedAt = qmidxDroppedAt.row()
			case self.DropIndicatorPosition.BelowItem:
				pItemDroppedAt = tItemDroppedAt.parent() or self.invisibleRootItem()
				idxDroppedAt = qmidxDroppedAt.row() + 1
			case self.DropIndicatorPosition.OnItem:
				if(sourceItemDragged == tItemDroppedAt):
					return
				pItemDroppedAt = tItemDroppedAt
				idxDroppedAt = tItemDroppedAt.childCount()
			case self.DropIndicatorPosition.OnViewport:
				pItemDroppedAt = self.invisibleRootItem()
				idxDroppedAt = self.invisibleRootItem().childCount()

		if(e.source() != self):
			e.setDropAction(Qt.DropAction.CopyAction)
			droppedNode = self.getAttachedNode(sourceItemDragged).copy()
		else:
			e.setDropAction(Qt.DropAction.MoveAction)
			droppedNode = self.getAttachedNode(sourceItemDragged)
			if(sourcePItemDragged == pItemDroppedAt):
				oldIdx = sourcePItemDragged.indexOfChild(sourceItemDragged)
				if(idxDroppedAt > oldIdx):
					idxDroppedAt -= 1

		self.pauseItemUpdates = True
		super().dropEvent(e)

		tItemDropped = pItemDroppedAt.child(idxDroppedAt)
		pNodeDroppedAt = self.getAttachedNode(pItemDroppedAt)

		pNodeDroppedAt.addChild(droppedNode, idxDroppedAt)
		if(e.dropAction() == Qt.DropAction.CopyAction):
			if(droppedNode.type() == FNodeType.CONSTANT):
				tItemDropped.setFlags(tItemDropped.flags() | Qt.ItemFlag.ItemIsEditable)
			if(droppedNode.children()):
				[self.createItems(c, tItemDropped) for c in droppedNode.children()]
		# else:
		# 	pNodeDroppedAt.addChild(droppedNode, idxDroppedAt)

		self.attachNodeID(tItemDropped, droppedNode)
		pItemDroppedAt.setExpanded(True)
		self.pauseItemUpdates = False
		e.source().lastDragged = tItemDropped


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
		