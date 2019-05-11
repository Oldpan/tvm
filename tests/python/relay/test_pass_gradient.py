# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
import tvm
from tvm import relay
from tvm.relay.ir_pass import free_vars, free_type_vars, gradient
from tvm.relay import create_executor
from tvm.relay.prelude import Prelude

import numpy as np


def rand(dtype='float32', *shape):
    return tvm.nd.array(np.random.rand(*shape).astype(dtype))


def test_id():
    shape = (10, 10)
    dtype = 'float32'
    t = relay.TensorType(shape, dtype)
    x = relay.var("x", t)
    func = relay.Function([x], x)
    back_func = relay.ir_pass.infer_type(gradient(func))
    assert back_func.checked_type == relay.FuncType([t], relay.TupleType([t, relay.TupleType([t])]))
    ex = create_executor()
    x = rand(dtype, *shape)
    forward, (grad,) = ex.evaluate(back_func)(x)
    tvm.testing.assert_allclose(forward.asnumpy(), x.asnumpy())
    tvm.testing.assert_allclose(grad.asnumpy(), np.ones_like(x.asnumpy()))


def test_add():
    shape = (10, 10)
    dtype = 'float32'
    t = relay.TensorType(shape, dtype)
    x = relay.var("x", t)
    func = relay.Function([x], x + x)
    back_func = relay.ir_pass.infer_type(gradient(func))
    assert back_func.checked_type == relay.FuncType([t], relay.TupleType([t, relay.TupleType([t])]))
    ex = create_executor()
    x = rand(dtype, *shape)
    forward, (grad,) = ex.evaluate(back_func)(x)
    tvm.testing.assert_allclose(forward.asnumpy(), 2 * x.asnumpy())
    tvm.testing.assert_allclose(grad.asnumpy(), 2 * np.ones_like(x.asnumpy()))


def test_temp_add():
    shape = (10, 10)
    dtype = 'float32'
    t = relay.TensorType(shape, dtype)
    x = relay.var("x", t)
    y = x + x
    func = relay.Function([x], y + y)
    back_func = relay.ir_pass.infer_type(gradient(func))
    assert back_func.checked_type == relay.FuncType([t], relay.TupleType([t, relay.TupleType([t])]))
    ex = create_executor()
    x = rand(dtype, *shape)
    forward, (grad,) = ex.evaluate(back_func)(x)
    tvm.testing.assert_allclose(forward.asnumpy(), 4 * x.asnumpy())
    tvm.testing.assert_allclose(grad.asnumpy(), 4 * np.ones_like(x.asnumpy()))


def test_sub():
    shape = (10, 10)
    dtype = 'float32'
    t = relay.TensorType(shape, dtype)
    x = relay.var("x", t)
    func = relay.Function([x], x - x)
    back_func = relay.ir_pass.infer_type(gradient(func))
    assert back_func.checked_type == relay.FuncType([t], relay.TupleType([t, relay.TupleType([t])]))
    ex = create_executor()
    x = rand(dtype, *shape)
    forward, (grad,) = ex.evaluate(back_func)(x)
    tvm.testing.assert_allclose(forward.asnumpy(), np.zeros_like(x.asnumpy()))
    tvm.testing.assert_allclose(grad.asnumpy(), np.zeros_like(x.asnumpy()))


def test_broadcast_add():
    shape1 = (3, 4, 1)
    shape2 = (1, 5)
    dtype = 'float32'
    x_nd = rand(dtype, *shape1)
    y_nd = rand(dtype, *shape2)
    x_np = x_nd.asnumpy()
    y_np = y_nd.asnumpy()
    expected_forward = x_np + y_np
    t1 = relay.TensorType(shape1, dtype)
    t2 = relay.TensorType(shape2, dtype)
    x = relay.var("x", t1)
    y = relay.var("y", t2)
    func = relay.Function([x, y], x + y)
    full_func = relay.ir_pass.infer_type(gradient(func))
    assert full_func.checked_type == relay.FuncType([t1, t2],
                                                    relay.TupleType([relay.TensorType(expected_forward.shape, dtype),
                                                                     relay.TupleType([t1, t2])]))
    ex = create_executor()
    forward, (grad_x, grad_y) = ex.evaluate(full_func)(x_nd, y_nd)
    tvm.testing.assert_allclose(forward.asnumpy(), expected_forward)
    tvm.testing.assert_allclose(grad_x.asnumpy(),
                                np.ones_like(expected_forward).sum(axis=2, keepdims=True))
    tvm.testing.assert_allclose(grad_y.asnumpy(),
                                np.ones_like(expected_forward).sum(axis=(0, 1), keepdims=True).squeeze(axis=0))


def test_broadcast_subtract():
    shape1 = (3, 4, 1)
    shape2 = (1, 5)
    dtype = 'float32'
    x_nd = rand(dtype, *shape1)
    y_nd = rand(dtype, *shape2)
    x_np = x_nd.asnumpy()
    y_np = y_nd.asnumpy()
    expected_forward = x_np - y_np
    t1 = relay.TensorType(shape1, dtype)
    t2 = relay.TensorType(shape2, dtype)
    x = relay.var("x", t1)
    y = relay.var("y", t2)
    func = relay.Function([x, y], x - y)
    full_func = relay.ir_pass.infer_type(gradient(func))
    assert full_func.checked_type == relay.FuncType([t1, t2],
                                                    relay.TupleType([relay.TensorType(expected_forward.shape, dtype),
                                                                     relay.TupleType([t1, t2])]))
    ex = create_executor()
    forward, (grad_x, grad_y) = ex.evaluate(full_func)(x_nd, y_nd)
    tvm.testing.assert_allclose(forward.asnumpy(), expected_forward)
    tvm.testing.assert_allclose(grad_x.asnumpy(),
                                np.ones_like(expected_forward).sum(axis=2, keepdims=True))
    tvm.testing.assert_allclose(grad_y.asnumpy(),
                                -np.ones_like(expected_forward).sum(axis=(0, 1), keepdims=True).squeeze(axis=0))


def test_tuple():
    shape = (10, 10)
    dtype = 'float32'
    t = relay.TensorType(shape, dtype)
    x = relay.var("x", t)
    y = relay.var("y", t)
    z = relay.var("z", t)
    tup = relay.Var("tup")
    func = relay.Function([x, y, z], relay.Let(tup, relay.Tuple([x, y, z]),
                                               relay.TupleGetItem(tup, 0) +
                                               relay.TupleGetItem(tup, 1) -
                                               relay.TupleGetItem(tup, 2)))
    back_func = relay.ir_pass.infer_type(gradient(func))
    assert back_func.checked_type == relay.FuncType([t, t, t], relay.TupleType([t, relay.TupleType([t, t, t])]))
    x_nd = rand(dtype, *shape)
    y_nd = rand(dtype, *shape)
    z_nd = rand(dtype, *shape)
    x_np = x_nd.asnumpy()
    y_np = y_nd.asnumpy()
    z_np = z_nd.asnumpy()
    expected_forward = x_np + y_np - z_np
    ex = create_executor()
    forward, (grad_x, grad_y, grad_z) = ex.evaluate(back_func)(x_nd, y_nd, z_nd)
    tvm.testing.assert_allclose(forward.asnumpy(), expected_forward)
    tvm.testing.assert_allclose(grad_x.asnumpy(), np.ones_like(grad_x.asnumpy()))
    tvm.testing.assert_allclose(grad_y.asnumpy(), np.ones_like(grad_y.asnumpy()))
    tvm.testing.assert_allclose(grad_z.asnumpy(), -1 * np.ones_like(grad_z.asnumpy()))


def test_pow():
    mod = relay.Module()
    p = Prelude(mod)
    shape = (10, 10)
    dtype = 'float32'
    t = relay.TensorType(shape, dtype)
    x = relay.var("x", t)
    double = relay.Function([x], x + x)
    i = relay.var("i", t)
    func = relay.Function([i], relay.Call(p.iterate(double, p.s(p.s(p.s(p.z())))), [i]))
    back_func = relay.ir_pass.infer_type(gradient(func, mod=mod), mod=mod)
    assert back_func.checked_type == relay.FuncType([t], relay.TupleType([t, relay.TupleType([t])]))
    i_nd = rand(dtype, *shape)
    ex = create_executor(mod=mod)
    forward, (grad_i,) = ex.evaluate(back_func)(i_nd)
    tvm.testing.assert_allclose(forward.asnumpy(), 8 * i_nd.asnumpy())
    tvm.testing.assert_allclose(grad_i.asnumpy(), 8 * np.ones_like(grad_i.asnumpy()))


def test_ref():
    shape = (10, 10)
    dtype = 'float32'
    t = relay.TensorType(shape, dtype)
    x = relay.var("x", t)
    r = relay.Var("r")
    u = relay.Var("u")
    body = relay.RefRead(r)
    body = relay.Let(u, relay.RefWrite(r, relay.RefRead(r) + relay.RefRead(r)), body)
    body = relay.Let(r, relay.RefCreate(x), body)
    func = relay.Function([x], body)
    back_func = relay.ir_pass.infer_type(gradient(func))
    assert back_func.checked_type == relay.FuncType([t], relay.TupleType([t, relay.TupleType([t])]))
    x_nd = rand(dtype, *shape)
    ex = create_executor()
    forward, (grad_x,) = ex.evaluate(back_func)(x_nd)
    tvm.testing.assert_allclose(forward.asnumpy(), 2 * x_nd.asnumpy())
    tvm.testing.assert_allclose(grad_x.asnumpy(), 2 * np.ones_like(grad_x.asnumpy()))


def test_square_second_order():
    shape = (10, 10)
    dtype = 'float32'
    t = relay.TensorType(shape, dtype)
    x = relay.var("x", t)
    func = relay.Function([x], x * x)
    back_func = relay.ir_pass.infer_type(gradient(func))
    y = relay.var("y", t)
    back_func_adjusted = relay.Function([y], relay.TupleGetItem(relay.TupleGetItem(back_func(y), 1), 0))
    back_func_adjusted = relay.ir_pass.infer_type(back_func_adjusted)
    back_back_func = relay.ir_pass.infer_type(gradient(back_func_adjusted))
    assert back_func.checked_type == relay.FuncType([t], relay.TupleType([t, relay.TupleType([t])]))
    x_nd = rand(dtype, *shape)
    ex = create_executor()
    forward, (grad_x,) = ex.evaluate(back_back_func)(x_nd)
    tvm.testing.assert_allclose(forward.asnumpy(), 2 * x_nd.asnumpy())
    tvm.testing.assert_allclose(grad_x.asnumpy(), 2 * np.ones_like(grad_x.asnumpy()))


if __name__ == "__main__":
    test_id()
    test_add()
    test_temp_add()
    test_sub()
    test_broadcast_add()
    test_broadcast_subtract()
    test_tuple()
    test_pow()
    test_ref()
    test_square_second_order()
