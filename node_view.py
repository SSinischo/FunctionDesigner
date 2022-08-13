from PyQt6.QtWidgets import *
from PyQt6.QtGui import *
from PyQt6.QtCore import *
from fnode import FNode, FNodeType
from stylesheets import *


class NodeView(QTreeWidget):
	ITALIC_FONT = QFont('Segoe UI', 9, italic=True)
	
	def __init__(self):
		super(QTreeWidget, self).__init__()
		self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
		self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
		self.setHeaderHidden(True)
		self.setDragDropMode(self.DragDropMode.DragDrop)
		self.setAcceptDrops(True)
		self.setColumnCount(3)
		self.setColumnWidth(1, 50)
		self.setColumnWidth(2, 25)
		self.header().setStretchLastSection(False)
		self.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)

		self.tItemsByNodeID = {}
		self.rootNode = FNode(FNodeType.ROOT)
		self.attachNode(self.invisibleRootItem(), self.rootNode)

		self.blockItemUpdates = True

	
	def selectedItem(self) -> QTreeWidgetItem:
		tItems = self.selectedItems()
		return tItems[0] if tItems else None
	

	def attachNode(self, tItem: QTreeWidgetItem, n: FNode):
		tItem.setData(0, Qt.ItemDataRole.UserRole, n.nodeID())
		tItem.setText(2, str(n.nodeID()))
		self.tItemsByNodeID[n.nodeID()] = tItem
	

	def attachedNode(self, tItem: QTreeWidgetItem) -> FNode:
		return FNode.getNode(tItem.data(0, Qt.ItemDataRole.UserRole)) if tItem else None
	

	def selectedNode(self) -> FNode:
		return self.attachedNode(self.selectedItem())


	# Ensure FNode heirarchy is up to date before calling
	def createTreeItems(self, n, pItem=None, idx=None):
		if(n.type() == FNodeType.ROOT):
			for c in n.children():
				self.createTreeItems(c, self.invisibleRootItem())
			return
		pItem = pItem or self.tItemsByNodeID.get(n.parent())
		idx = n.parent().children().index(n) if idx is None else idx
		tItem = QTreeWidgetItem()
		self.attachNode(tItem, n)

		if(n.name()):
			tItem.setText(0, n.name())
			tItem.setFont(0, NodeView.ITALIC_FONT)
		else:
			tItem.setText(0, FNode.TYPE_NAMES[n.type()])
		if(n.type() == FNodeType.CONSTANT):
			tItem.setText(0, tItem.text(0) or n.formula())
			tItem.setFlags(tItem.flags() | Qt.ItemFlag.ItemIsEditable)
		elif(n.type() == FNodeType.VARIABLE):
			tItem.setText(1, 'variable')
			tItem.setFont(1, NodeView.ITALIC_FONT)
		elif(n.type() == FNodeType.FUNCTION):
			tItem.setText(1, 'function')
			tItem.setFont(1, NodeView.ITALIC_FONT)
		elif(n.isNegated()):
			tItem.setText(0, '-'+tItem.text(0))
		
		pItem.insertChild(idx, tItem)
		for c in n.children():
			self.createTreeItems(c, tItem)
		pItem.setExpanded(True)
		return tItem
	

	def deleteItem(self, tItem:QTreeWidgetItem):
		n = self.attachedNode(tItem)
		n.delete()
		pItem = tItem.parent() or self.invisibleRootItem()
		pItem.removeChild(tItem)
	

	def deleteSelectedItem(self, warnIfChildren=True):
		tItem = self.selectedItem()
		if(not tItem):
			return False
		n = self.attachedNode(tItem)
		if(warnIfChildren and n.children()):
			msg = QMessageBox()
			msg.setText('The selected node is not a leaf.  Are you sure you want to delete the selected node and all of its children?')
			msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
			r = msg.exec()
			if(not r):
				return
		return self.deleteItem(tItem)
	

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
		pn = self.attachedNode(pItem)
		n = FNode.fromString(QApplication.clipboard().text())
		if(n):
			pn.addChild(n)
			self.createTreeItems(n, pItem)
			return True
		return False


	def onItemUpdated(self, itemUpdated):
		if(self.blockItemUpdates):
			return
		n = self.attachedNode(itemUpdated[0])
		if(not n or n.type() != FNodeType.CONSTANT):
			return
		try:
			n.setConstantValue(float(itemUpdated[0].text(0)))
		except:
			itemUpdated[0].setText(0, '0')
	

	def replaceSelectedNode(self, n):
		tItem = self.selectedItem()
		if(not tItem):
			self.invisibleRootItem().takeChildren()
			[c.delete() for c in self.rootNode.children()]
			pItem = self.invisibleRootItem()
			idx = None
		else:
			pItem = tItem.parent() or self.invisibleRootItem()
			idx = pItem.indexOfChild(tItem)
			self.deleteItem(tItem)
			pItem.removeChild(tItem)
		self.attachedNode(pItem).addChild(n, idx)
		tItem = self.createTreeItems(n, pItem, idx)
		self.clearSelection()
		tItem.setSelected(True)


	def startDrag(self, supportedActions):
		self.lastDraggedItem = self.selectedItem()
		return super().startDrag(supportedActions)


	def dropEvent(self, e: QDropEvent):
		if(not isinstance(e.source(), NodeView)):
			e.ignore()
			return
	
		#itemFromIndex
		#itemAbove
		#itemBelow
		sourceItemDragged = e.source().selectedItem()
		sourcePItemDragged = sourceItemDragged.parent() or self.invisibleRootItem()
		ePos = e.position().toPoint()
		tItemDroppedAt = self.itemAt(ePos)

		match(self.dropIndicatorPosition()):
			case self.DropIndicatorPosition.AboveItem:
				newPItem = tItemDroppedAt.parent() or self.invisibleRootItem()
				newIdx = self.indexAt(ePos).row()
			case self.DropIndicatorPosition.BelowItem:
				newPItem = tItemDroppedAt.parent() or self.invisibleRootItem()
				newIdx = self.indexAt(ePos).row() + 1
			case self.DropIndicatorPosition.OnItem:
				if(sourceItemDragged == tItemDroppedAt):
					return
				newPItem = tItemDroppedAt
				newIdx = tItemDroppedAt.childCount()
			case self.DropIndicatorPosition.OnViewport:
				newPItem = self.invisibleRootItem()
				newIdx = self.invisibleRootItem().childCount()

		newParent = self.attachedNode(newPItem)

		if(e.source() != self):
			e.setDropAction(Qt.DropAction.CopyAction)
			droppedNode = self.attachedNode(sourceItemDragged).copy()
			newParent.addChild(droppedNode, newIdx)
			self.createTreeItems(droppedNode, newPItem, newIdx)
		else:
			e.setDropAction(Qt.DropAction.MoveAction)
			droppedNode = self.attachedNode(sourceItemDragged)
			if(sourcePItemDragged == newPItem):
				oldIdx = sourcePItemDragged.indexOfChild(sourceItemDragged)
				if(newIdx > oldIdx):
					newIdx -= 1
			newParent.addChild(droppedNode, newIdx)
			super().dropEvent(e)


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
		