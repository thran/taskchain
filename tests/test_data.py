from collections.abc import Generator
from pathlib import Path

from taskchain import Task, Config, InMemoryData, JSONData
from taskchain.data import DirData, NumpyData, PandasData, ContinuesData, GeneratedData

import numpy as np
import pandas as pd


def test_persistence(tmp_path):
    class A(Task):
        class Meta:
            task_group = 'x'

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.run_called = 0

        def run(self) -> int:
            self.run_called += 1
            return 1

    config = Config(tmp_path, name='test')

    a = A(config)
    assert a.value == 1
    assert a.run_called == 1
    assert a.value == 1
    assert a.run_called == 1

    assert (tmp_path / 'x' / 'a' / 'test.json').exists()

    a2 = A(config)
    assert a2.value == 1
    assert a2.run_called == 0

    config2 = Config(tmp_path, name='test2')

    a3 = A(config2)
    assert a3.value == 1
    assert a3.run_called == 1


def test_object_persistence(tmp_path):
    class A(Task):
        class Meta:
            task_group = 'x'

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.run_called = 0

        def run(self) -> JSONData:
            self.run_called += 1
            data = JSONData()
            data.set_value(1)
            return data

    config = Config(tmp_path, name='test')

    a = A(config)
    assert a.value == 1
    assert a.run_called == 1
    assert a.value == 1
    assert a.run_called == 1

    assert (tmp_path / 'x' / 'a' / 'test.json').exists()

    a2 = A(config)
    assert a2.value == 1
    assert a2.run_called == 0

    config2 = Config(tmp_path, name='test2')

    a3 = A(config2)
    assert a3.value == 1
    assert a3.run_called == 1


def test_in_memory_data(tmp_path):
    class A(Task):
        class Meta:
            task_group = 'x'
            data_class = InMemoryData

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.run_called = 0

        def run(self) -> int:
            self.run_called += 1
            return 1

    config = Config(tmp_path, name='test')

    a = A(config)
    assert a.value == 1
    assert a.run_called == 1
    assert a.value == 1
    assert a.run_called == 1

    assert (tmp_path / 'x' / 'a').exists()

    a2 = A(config)
    assert a2.value == 1
    assert a2.run_called == 1


def test_returned_in_memory_data(tmp_path):
    class MyData(InMemoryData):
        def __init__(self, a):
            super().__init__()
            self.set_value(a)

    class B(Task):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.run_called = 0

        def run(self) -> MyData:
            self.run_called += 1
            data = MyData(1)
            return data

    config = Config(tmp_path, name='test')

    b = B(config)
    assert b.value == 1
    assert b.run_called == 1
    assert b.value == 1
    assert b.run_called == 1

    assert not (tmp_path / 'x' / 'b').exists()

    a2 = B(config)
    assert a2.value == 1
    assert a2.run_called == 1


def test_dir_data(tmp_path):
    class C(Task):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.run_called = 0

        def run(self) -> DirData:
            self.run_called += 1
            data = self.get_data_object()
            assert isinstance(data.dir, Path)
            assert data.dir == tmp_path / 'c' / 'test_tmp'
            (data.dir / 'c').mkdir()
            return data

    config = Config(tmp_path, name='test')
    c = C(config)
    assert not (tmp_path / 'c' / 'test').exists()
    _ = c.value
    assert (tmp_path / 'c' / 'test').exists()
    assert c.value == tmp_path / 'c' / 'test'
    assert c.run_called == 1
    assert (c.value / 'c').exists()

    c2 = C(config)
    assert c.value == tmp_path / 'c' / 'test'
    assert c2.run_called == 0

    assert (c.value / 'c').exists()
    c2.data.delete()
    assert not (c.value / 'c').exists()


def test_numpy_data(tmp_path):
    data = NumpyData()
    data.init_persistence(tmp_path, 'test')
    data.set_value(np.zeros((10, 10)))
    data.save()

    assert (tmp_path / 'test.npy').exists()
    assert data.is_data_type_accepted(np.ndarray)

    data2 = NumpyData()
    data2.init_persistence(tmp_path, 'test')
    data2.load(np.ndarray)

    assert data2.value.shape == (10, 10)
    data.delete()
    assert not (tmp_path / 'test.npy').exists()


def test_pandas_data(tmp_path):
    data = PandasData()
    data.init_persistence(tmp_path, 'test')
    data.set_value(pd.DataFrame([[0, 1], [2, 3]]))
    data.save()

    assert (tmp_path / 'test.pd').exists()
    assert data.is_data_type_accepted(pd.DataFrame)
    assert data.is_data_type_accepted(pd.Series)

    data2 = PandasData()
    data2.init_persistence(tmp_path, 'test')
    data2.load(pd.DataFrame)

    assert data2.value.shape == (2, 2)
    data.delete()
    assert not (tmp_path / 'test.pd').exists()


def test_generator_data(tmp_path):
    data = GeneratedData()
    data.init_persistence(tmp_path, 'test')

    def _gen():
        yield from range(10)

    data.set_value(_gen())
    data.save()

    assert (tmp_path / 'test.jsonl').exists()
    assert data.is_data_type_accepted(Generator)

    data2 = GeneratedData()
    data2.init_persistence(tmp_path, 'test')
    data2.load(Generator)

    assert data2.value == list(range(10))
    data.delete()
    assert not (tmp_path / 'test.jsonl').exists()


def test_continues_data(tmp_path):
    class D(Task):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.run_called = 0

        def run(self) -> ContinuesData:
            data = self.get_data_object()
            for i in range(4):
                new = data.dir / str(i)
                if not new.exists():
                    new.mkdir()
                    self.run_called += 1
                    if i == 3:
                        data.finished()
                    break

            return data

    config = Config(tmp_path, name='test')
    d = D(config)
    assert not (tmp_path / 'd' / 'test').exists()
    assert not (tmp_path / 'd' / 'test_tmp').exists()
    _ = d.value
    assert not (tmp_path / 'd' / 'test').exists()
    assert (tmp_path / 'd' / 'test_tmp').exists()
    assert d.value == tmp_path / 'd' / 'test_tmp'
    assert d.run_called == 1
    assert (d.value / '0').exists()
    assert not (d.value / '1').exists()

    d2 = D(config)
    assert (tmp_path / 'd' / 'test_tmp').exists()
    _ = d2.value
    assert (tmp_path / 'd' / 'test_tmp').exists()
    assert d2.value == tmp_path / 'd' / 'test_tmp'
    assert d2.run_called == 1
    assert (d2.value / '0').exists()
    assert (d2.value / '1').exists()
    assert not (d2.value / '2').exists()

    _ = D(config).value
    assert (d2.value / '2').exists()

    d3 = D(config)
    _ = d3.value
    assert (d3.value / '3').exists()
    assert not (d3.value / '4').exists()
    assert (tmp_path / 'd' / 'test').exists()
    assert not (tmp_path / 'd' / 'test_tmp').exists()
    assert d3.value == tmp_path / 'd' / 'test'

    d4 = D(config)
    _ = d4.value
    assert d4.run_called == 0
    assert not (d4.value / '4').exists()

    d4.data.delete()
    assert not (tmp_path / 'test.npy').exists()


def test_run_info(tmp_path):
    d = JSONData()
    d.init_persistence(tmp_path, 'name')
    run_info = {'a': 1, 'b': ['asd']}
    d.save_run_info(run_info)

    assert (tmp_path / 'name.run_info.yaml').exists()
    loaded = d.load_run_info()
    assert loaded == run_info
    assert loaded['a'] == 1
