COMPOSITION_VIEW_STYLE = '''
    QTreeView::branch:has-siblings:!adjoins-item {
        border-image: url(img/vline.svg) 0;
    }

    QTreeView::branch:!has-children:has-siblings:adjoins-item {
        border-image: url(img/branch-more.svg) 0;
    }

    QTreeView::branch:!has-children:!has-siblings:adjoins-item {
        border-image: url(img/branch-end.svg) 0;
    }
    QTreeView::item:checked{
        border: 2px solid #FF0000;
    }
'''

    # QTreeView::branch:has-children:!has-siblings:closed,
    # QTreeView::branch:closed:has-children:has-siblings {
    #         border-image: none;
    #         image: url(img/branch-closed.svg);
    # }

    # QTreeView::branch:open:has-children:!has-siblings,
    # QTreeView::branch:open:has-children:has-siblings  {
    #         border-image: none;
    #         image: url(img/branch-open.svg);
    # }

QUICK_BUTTON_STYLE = '''
    QPushButton{
        padding: 0px;
        font-family: "Consolas";
        font-size: 18px;
        font-weight: 700;
    }
'''
