"""Bounded, thread-scoped teaching trace of the actual mission Python code.

Only allowlisted Python frames are traced. No frame locals, return values,
exception messages or external-library source are inspected. A line event means
Python is about to execute that source line; it does not prove a command worked.
"""
from __future__ import annotations

import ast
import collections
import contextlib
import functools
import hashlib
import math
from pathlib import Path
import sys
import threading
import time
import uuid


TRACE_FILES = ('control.py', 'vision.py')
SOURCE_FILES = TRACE_FILES + ('server.py', 'native_runtime.py')
CONTEXT_KEYS = frozenset(('mission', 'phase', 'phase_label', 'status', 'step_index',
                          'paused', 'goal_enu', 'servo_channel', 'pwm'))
WAIT_KEYS = frozenset(('goal_enu', 'position_enu', 'distance_m', 'altitude_error_m',
                       'speed_mps', 'command_id', 'paused'))
EXPLANATIONS = {
    'Controller.run_mission': 'Seçilen G1/G2/G3 görevini gerçek uçuş komutlarıyla yürütür.',
    'Controller._run_traced_mission': 'Yalnız görev iş parçacığı için Python satır izlemeyi açar.',
    'Controller.goto': 'ENU hedefini NED komutuna çevirir; ölçülen konum ve hız koşulunu bekler.',
    'Controller.wait': 'Gerçek koşulu tekrar denetler; iptal, bağlantı ve süre sınırını kontrol eder.',
    'Controller.command': 'MAVLink komutunu gönderir ve ArduPilot COMMAND_ACK yanıtını bekler.',
    'Controller.servo': 'İzin verilen servo kanalını ArduPilot üzerinden açar veya kapatır.',
    'Controller.takeoff': 'GUIDED, ARM ve kalkış komutlarını gerçek telemetriyle doğrular.',
    'Controller.release': 'Kamera hedefi ve kavrayıcı telemetrisiyle yaklaşır; salınım azalınca bırakır.',
    'Controller.phase': 'Görev aşamasını ve operatöre gösterilen ilerlemeyi günceller.',
    'Controller.vehicle': 'Son MAVLink mesajlarından ölçülen araç durumunu oluşturur.',
    'Controller.mode': 'ArduPilot uçuş modunu değiştirir ve kalp atışından doğrular.',
    'Controller.send': 'MAVLink gönderimini bir kilit altında seri hale getirir.',
    'Camera.update': 'Gerçek Gazebo RGB görüntüsünü okur; tespitleri ve kamera durumunu günceller.',
    'read_frame': 'Görüntü ile poz metadatasının güncel ve birbiriyle eşleşmiş olmasını denetler.',
    'detect': 'RGB renk ve şekil ölçümlerini fiziksel boyut denetimleriyle süzer.',
    'masks': 'HSV renk uzayında kırmızı ve mavi piksel maskelerini çıkarır.',
    'project': 'Kamera pikselinden dünyaya ışın çıkararak zemin kesişimini hesaplar.',
    'rotation': 'Kamera quaternion değerini normalize edip dönüş matrisine çevirir.',
}


def _safe(value, depth=0):
    """Copy only small JSON primitives; never stringify arbitrary objects."""
    if value is None or type(value) is bool:
        return value
    if type(value) in (int, float):
        return value if math.isfinite(value) else None
    if type(value) is str:
        return value[:160]
    if type(value) in (list, tuple) and depth < 2:
        return [_safe(x, depth + 1) for x in value[:8]]
    return None


def _functions(tree):
    result = []
    def visit(node, prefix=''):
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                name = prefix + child.name
                if not isinstance(child, ast.ClassDef):
                    doc = ast.get_docstring(child)
                    result.append(dict(name=name, line=child.lineno, lineno=child.lineno,
                        end_line=child.end_lineno,
                        explanation=EXPLANATIONS.get(name, doc.splitlines()[0] if doc else
                            'Bu fonksiyonun gerçek Python kaynak satırları gösterilir.')))
                visit(child, name + '.')
            else:
                visit(child, prefix)
    visit(tree)
    return result


class ExecutionTracer:
    """Record actual events without sleeping, disk I/O or control-side effects.

    ``capture`` affects only its calling thread and restores its previous trace.
    ``wrap`` is intended for an explicitly selected camera.update callable in its
    existing thread. Source is cached at construction, including its SHA256, so
    later edits cannot silently shift the displayed execution lines.
    """
    def __init__(self, root=None, *, capacity=4096, context=None,
                 trace_files=TRACE_FILES, source_files=SOURCE_FILES):
        self.root = Path(root or Path(__file__).parent).resolve()
        self.capacity = max(16, min(int(capacity), 32768))
        self._lock = threading.RLock()
        self._local = threading.local()
        self._events = collections.deque(maxlen=self.capacity)
        self._lanes = {}
        self._sources = {}
        self._paths = {}
        self._context = {}
        self._context_provider = context
        self._seq = self._dropped = self._trace_errors = 0
        self._run_id = None
        self._mission_id = None
        self._status = 'idle'
        self._started = None
        self._loaded_wall_time = time.time()
        for name in source_files:
            path = (self.root / name).resolve()
            if path.parent != self.root or path.name != name:
                raise ValueError('Source must be an allowlisted backend filename')
            if not path.is_file():
                continue
            raw = path.read_bytes()
            text = raw.decode('utf-8-sig')
            self._sources[name] = dict(file=name, sha256=hashlib.sha256(raw).hexdigest(),
                lines=text.splitlines(), line_count=len(text.splitlines()),
                functions=_functions(ast.parse(text)), trace_enabled=name in trace_files,
                loaded_wall_time=self._loaded_wall_time, cached=True)
            if name in trace_files:
                self._paths[str(path)] = name
        self._filename_cache = {}

    def catalog(self):
        with self._lock:
            files = [{k: v for k, v in s.items() if k != 'lines'} for s in self._sources.values()]
        return dict(files=files, sample_interval_ms=250,
            note='Gerçek Python line/call/return/exception olayları; line, yürütülmek üzere olan satırdır. C/OpenCV içi ve yerel değişkenler izlenmez.')

    def source(self, file):
        if not isinstance(file, str) or file not in self._sources:
            raise ValueError('Source file is not allowlisted')
        with self._lock:
            item = self._sources[file]
            result = dict(item, lines=list(item['lines']), functions=[dict(x) for x in item['functions']])
        try:
            result['disk_sha256'] = hashlib.sha256((self.root / file).read_bytes()).hexdigest()
        except OSError:
            result['disk_sha256'] = None
        result['source_changed'] = result['disk_sha256'] != result['sha256']
        return result

    def bind_context(self, provider):
        """Bind a new controller without replacing the process source snapshot."""
        if provider is not None and not callable(provider):
            raise TypeError('Trace context provider must be callable')
        with self._lock:
            self._context_provider = provider
            for state in self._lanes.values():
                state['context_due'] = 0.

    def update_context(self, **values):
        with self._lock:
            self._context = dict(self._context, **{k: _safe(v) for k, v in values.items() if k in CONTEXT_KEYS})

    def _name(self, filename):
        try:
            return self._filename_cache[filename]
        except KeyError:
            try:
                name = self._paths.get(str(Path(filename).resolve()))
            except (OSError, ValueError):
                name = None
            self._filename_cache[filename] = name
            return name

    def is_capturing(self):
        return getattr(self._local, 'state', None) is not None

    @contextlib.contextmanager
    def capture(self, mission_id=None, *, lane='mission'):
        if lane not in ('mission', 'vision'):
            raise ValueError('Trace lane must be mission or vision')
        if self.is_capturing():
            yield self
            return
        previous = sys.gettrace()
        state = dict(lane=lane, stack=[], wait_stack=[], last=None, active=True,
                     thread_id=threading.get_ident(), context_due=0.)
        with self._lock:
            if lane == 'mission':
                self._events.clear()
                # Sequence remains monotonic across missions so an HTTP cursor
                # from the preceding run cannot suppress the new run's events.
                self._dropped = self._trace_errors = 0
                for old_state in self._lanes.values():
                    old_state['last'] = None
                    old_state['last_stack'] = None
                self._run_id = uuid.uuid4().hex
                self._mission_id = str(mission_id)[:32] if mission_id is not None else None
                self._status = 'running'
                self._started = time.monotonic()
                self._context = dict(mission=self._mission_id, status='running')
            self._lanes[lane] = state
        self._local.state = state
        try:
            sys.settrace(self._trace)
            yield self
        except BaseException:
            if lane == 'mission':
                self.finish('failed')
            raise
        finally:
            sys.settrace(previous)
            self._local.state = None
            with self._lock:
                state['active'] = False
                state['wait_stack'].clear()
                if lane == 'mission' and self._status == 'running':
                    self._status = 'finished'

    def wrap(self, function, *, lane='vision'):
        @functools.wraps(function)
        def wrapped(*args, **kwargs):
            with self.capture(lane=lane):
                return function(*args, **kwargs)
        return wrapped

    def finish(self, status='finished'):
        with self._lock:
            self._status = status if status in ('completed', 'failed', 'paused', 'cancelled', 'finished') else 'finished'
            self._context = dict(self._context, status=self._status)

    def _trace(self, frame, event, arg):
        name = self._name(frame.f_code.co_filename)
        if name is None:
            return None
        if event not in ('call', 'line', 'return', 'exception'):
            return self._trace
        state = getattr(self._local, 'state', None)
        if state is None:
            return None
        try:
            now = time.monotonic()
            # Context comes from an explicit provider, never from frame.f_locals.
            values = None
            if self._context_provider is not None and now >= state['context_due']:
                state['context_due'] = now + .25
                try:
                    values = self._context_provider()
                except Exception:
                    pass
            with self._lock:
                if isinstance(values, dict):
                    self._context = dict(self._context, **{k: _safe(v) for k, v in values.items() if k in CONTEXT_KEYS})
                stack = state['stack']
                identity = id(frame)
                node = dict(file=name, function=frame.f_code.co_qualname,
                            line=frame.f_lineno, lineno=frame.f_lineno)
                if stack and stack[-1][0] == identity:
                    stack[-1] = (identity, node)
                else:
                    # Handles call, generators and a capture entered inside an
                    # already running frame, without retaining frame objects.
                    parents = []
                    parent = frame.f_back
                    while parent is not None:
                        parent_name = self._name(parent.f_code.co_filename)
                        if parent_name is not None:
                            parents.append((id(parent), dict(file=parent_name,
                                function=parent.f_code.co_qualname,
                                line=parent.f_lineno, lineno=parent.f_lineno)))
                        parent = parent.f_back
                    stack[:] = list(reversed(parents)) + [(identity, node)]
                self._seq += 1
                row = dict(seq=self._seq, event=event, wall_time=time.time(),
                    monotonic_s=now, elapsed_s=now-self._started if self._started is not None else 0.,
                    lane=state['lane'], thread_id=state['thread_id'], **node,
                    phase=self._context.get('phase'), context=self._context)
                if event == 'exception':
                    row['exception_type'] = arg[0].__name__
                if len(self._events) == self.capacity:
                    self._dropped += 1
                self._events.append(row)
                state['last'] = row
                # Keep the actual return/exception stack available while the
                # thread is sleeping outside Python; copied only on those events.
                state['last_stack'] = [x[1] for x in stack] if event in ('return', 'exception') else None
                if event == 'return' and stack:
                    stack.pop()
        except Exception:
            # A display fault must never become an aircraft-control exception.
            with self._lock:
                self._trace_errors += 1
        return self._trace

    @contextlib.contextmanager
    def waiting(self, kind, description, timeout_s, **details):
        state = getattr(self._local, 'state', None)
        if state is None:
            yield
            return
        wait = dict(kind=str(kind)[:32], description=str(description)[:160],
                    timeout_s=float(timeout_s), started_monotonic=time.monotonic(),
                    **{k: _safe(v) for k, v in details.items() if k in WAIT_KEYS})
        with self._lock:
            state['wait_stack'].append(wait)
        try:
            yield
        finally:
            with self._lock:
                if wait in state['wait_stack']:
                    state['wait_stack'].remove(wait)

    def update_wait(self, **details):
        state = getattr(self._local, 'state', None)
        if state is not None:
            with self._lock:
                if state['wait_stack']:
                    state['wait_stack'][-1].update({k: _safe(v) for k, v in details.items() if k in WAIT_KEYS})

    def _summary_locked(self, now):
        lanes = {}
        for name, state in self._lanes.items():
            current = dict(state['last']) if state['last'] else None
            if current is not None:
                current['context'] = dict(current['context'])
                current['stack'] = [dict(x) for x in (state.get('last_stack') or [x[1] for x in state['stack']])]
                current['active'] = state['active']
                current['age_s'] = max(0., now-current['monotonic_s'])
                current['sampled_wall_time'] = time.time()
                current['wait'] = None
                if state['wait_stack']:
                    wait = dict(state['wait_stack'][-1])
                    wait['elapsed_s'] = max(0., now-wait.pop('started_monotonic'))
                    current['wait'] = wait
            lanes[name] = current
        return dict(run_id=self._run_id, mission_id=self._mission_id, status=self._status,
            active=bool(self._lanes.get('mission', {}).get('active')), seq=self._seq,
            oldest_seq=self._events[0]['seq'] if self._events else self._seq+1,
            dropped=self._dropped, trace_errors=self._trace_errors, sample_interval_ms=250,
            current=lanes.get('mission'), lanes=lanes,
            source_sha256={k: v['sha256'] for k, v in self._sources.items()})

    def summary(self):
        with self._lock:
            return self._summary_locked(time.monotonic())

    def snapshot(self, after_seq=0, limit=120):
        after_seq = max(0, int(after_seq))
        limit = max(0, min(int(limit), 500))
        with self._lock:
            result = self._summary_locked(time.monotonic())
            pending = [e for e in self._events if e['seq'] > after_seq]
            result['events'] = [dict(e, context=dict(e['context'])) for e in pending[-limit:]] if limit else []
            result['skipped'] = max(0, len(pending)-limit)
            result['cursor_ahead'] = after_seq > self._seq
            return result


def traced_wait(kind):
    """Annotate an actual blocking operation; does not trace or issue commands."""
    def decorate(function):
        @functools.wraps(function)
        def wrapped(controller, *args, **kwargs):
            tracer = getattr(controller, 'execution', None)
            if tracer is None or not tracer.is_capturing():
                return function(controller, *args, **kwargs)
            if kind == 'goto':
                goal = args[0] if args else kwargs.get('goal')
                details = dict(goal_enu=[float(x) for x in goal])
                description, timeout = 'Ölçülen konum ve hız hedefi', kwargs.get('timeout', args[3] if len(args)>3 else 100)
            elif kind == 'wait':
                details = {}
                description = kwargs.get('description', args[2] if len(args)>2 else 'Koşul')
                timeout = kwargs.get('timeout', args[1] if len(args)>1 else 30)
            else:
                details = dict(command_id=int(args[0] if args else kwargs['cmd']))
                description, timeout = 'ArduPilot COMMAND_ACK', kwargs.get('timeout', 5)
            with tracer.waiting(kind, description, timeout, **details):
                return function(controller, *args, **kwargs)
        return wrapped
    return decorate
