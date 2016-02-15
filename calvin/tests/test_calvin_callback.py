from mock import Mock

from calvin.utilities.calvin_callback import CalvinCB, CalvinCBGroup, CalvinCBClass


def test_call_callback():
    func = Mock()
    cb = CalvinCB(func=func)
    cb()
    assert func.called


def test_call_callback_with_args():
    func = Mock()
    cb = CalvinCB(func, 1, 2, 3)
    cb()
    func.assert_called_with(1, 2, 3)


def test_call_callback_with_kwargs():
    func = Mock()
    cb = CalvinCB(func, a=1, b=2, c=3)
    cb()
    func.assert_called_with(a=1, b=2, c=3)


def test_args_update():
    func = Mock()
    cb = CalvinCB(func, 1, 2)
    cb.args_append(3)
    cb()
    func.assert_called_with(1, 2, 3)


def test_kwargs_update():
    func = Mock()
    cb = CalvinCB(func, 1, b=2)
    cb.kwargs_update(c=3)
    cb()
    func.assert_called_with(1, b=2, c=3)


def test_calvin_cb_group():
    func1 = Mock()
    func2 = Mock()
    cb1 = CalvinCB(func1)
    cb2 = CalvinCB(func2)
    cbs = CalvinCBGroup([cb1, cb2])
    cbs(1, 2, a=3)

    func1.assert_called_with(1, 2, a=3)
    func2.assert_called_with(1, 2, a=3)


def test_calvin_cb_class():
    func = Mock()
    cb = CalvinCB(func)

    func2 = Mock()
    cb2 = CalvinCB(func2)

    cb = CalvinCBClass(callbacks={'f': [cb]})
    assert 'f' in cb.callback_valid_names()

    cb.callback_register('f2', cb2)
    assert 'f2' in cb.callback_valid_names()

    cb.callback_unregister(cb2.id)
    assert 'f2' not in cb.callback_valid_names()

    cb._callback_execute('f', 1, 2, a=3)
    func.assert_called_with(1, 2, a=3)
