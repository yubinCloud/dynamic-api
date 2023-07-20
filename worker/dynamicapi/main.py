from fastapi import FastAPI, Body, Depends, Request, status, APIRouter, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse
from pydantic import BaseModel, Field, field_validator
import uvicorn
import re
from typing import Annotated, Callable
from sqlalchemy import create_engine, Engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from typing import List, Dict, Tuple

from config import settings
from schema.resp import R
from schema.meta import ParamFieldInfo, ParamFieldType, typed_map
from service import code_service
from exception import SQLParseException

app_conf = settings.app

app = FastAPI(
    title=app_conf.name,
    version='0.1.0'
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get('/health/live',
         response_model=R[str])
async def health_check():
    return R.success("health")


######################### exception handler #######################
@app.exception_handler(SQLAlchemyError)
def sqlalchemy_error_handler(request: Request, exc: SQLAlchemyError):
    return ORJSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=R.fail(str(exc)).dict()
    )


@app.exception_handler(SQLParseException)
def sql_parse_exception_handler(request: Request, exc: SQLParseException):
    return ORJSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=R.fail(str(exc)).dict()
    )

######################### internal router ###########################
meta_router = APIRouter(prefix='/meta', tags=['META API'])

engine_map = {}

engine_map['152'] = create_engine('mysql+pymysql://root:yubin3869@localhost:3306/sso_auth')


def use_engine(engine_id: str) -> Callable[[], Engine | None]:
    return lambda: engine_map.get(engine_id)


class ExecCodeArgs(BaseModel):
    code: str

    @field_validator('code')
    def verify_code(cls, value):
        if '"""' in value:
            raise ValueError('不能存在连续的三个引号')
        return value


class ExecCodeResp(BaseModel):
    code: str


@meta_router.post(
    '/exec-code/raw',
    response_model=R[ExecCodeResp],
    summary='执行代码'
)
async def exec_code(
        args: ExecCodeArgs = Body(...)
):
    exec(args.code)
    return R.success(ExecCodeResp(code=args.code))


class ExecSqlCodeArgs(BaseModel):
    api: str = Field('/example')
    summary: str = Field(..., title='接口概述')
    description: str = Field('', title='接口描述')
    datasource: str = Field(..., title='数据源的 ID')
    sql: str = Field(..., title='要执行的 SQL')

    @field_validator('sql')
    def verify_code(cls, value):
        if not value:
            raise ValueError('SQL 不能为空')
        if '"""' in value:
            raise ValueError('SQL 中不能存在连续的三个引号')
        if value[-1] == '"':
            raise ValueError('SQL 的最后一个字符不能为双引号，建议以分号结尾')
        return value


class ExecSqlCodeResp(BaseModel):
    code: str = Field('实际执行的代码')


def _parse_sql_slot(slot: str) -> ParamFieldInfo:
    slot = slot[2:-1]
    splits = slot.split(',')
    if splits:
        var_name = splits[0].strip()
    else:
        raise SQLParseException("SQL 中 #{} 内参数名称不允许为空")
    typed = ParamFieldType.STRING
    if len(splits) > 1:
        annotated = splits[1].strip().lower()
        typed = typed_map.get(annotated, None)
        if typed is None:
            raise SQLParseException(f"参数 {var_name} 的类型标注不符合要求")
    return {
        'name': var_name,
        'typed': typed
    }


def _replace_param_wrapper() -> Tuple[Callable[[re.Match], str], Dict[str, ParamFieldInfo]]:
    params = {}

    def _replace_param(matched: re.Match):
        param_info = _parse_sql_slot(matched.group(0))
        var_name = param_info['name']
        typed = param_info['typed']
        params[var_name] = param_info
        replaced = ''
        match typed:
            case ParamFieldType.STRING:
                replaced = f"'{{args.{var_name}}}'"
            case ParamFieldType.INTEGER:
                replaced = f'{{args.{var_name}}}'
            case ParamFieldType.FLOAT:
                replaced = f'{{args.{var_name}}}'
        return replaced

    return _replace_param, params


@meta_router.post('/exec-code/sql',
                  response_model=R[ExecSqlCodeResp])
async def exec_sql_code(
        args: ExecSqlCodeArgs
):
    pattern = re.compile(r'#\{.+?\}')
    # 替换这些 params，比如将 #{name} 替换为 `{args.name}`
    replace_func, params = _replace_param_wrapper()
    sql_replaced = re.sub(pattern, replace_func, args.sql)
    # 生成所有的 Depends 代码的列表
    depends_list = []
    depends_list.append('engine = Depends(use_engine("152"))')
    code = code_service.create_sql_api(args.api, sql_replaced, params, depends_list, args.summary, args.description)
    print(code)
    exec(code)
    return R.success(ExecSqlCodeResp(code=code))


class EngineAddArgs(BaseModel):
    id: str = Field(..., title='engine 的 ID', description='后面获取 engine 需要依赖此 ID')
    url: str = Field(..., title='连接的 URL')


@meta_router.put(
    '/engine/add',
    response_model=R[str],
    summary='增加 Engine'
)
async def add_engine(
        args: EngineAddArgs = Body()
):
    engine_map[args.id] = create_engine(args.url)
    return R.success(f'engine {args.id} add success')


class EngineDeleteArgs(BaseModel):
    id: str = Field(..., title='所要删除的 engine 的 ID')


@meta_router.delete(
    '/engine/delete',
    response_model=R,
    summary='删除一个 Engine'
)
async def delete_engine(
    args: EngineDeleteArgs = Body()
):
    if args.id in engine_map:
        del engine_map[args.id]
    return R.success(f'engine {args.id} delete success')


app.include_router(meta_router)

if __name__ == '__main__':
    uvicorn.run(app, host=app_conf.host, port=app_conf.port)
