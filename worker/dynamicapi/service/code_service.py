from typing import List, Dict
from datetime import datetime

from schema.meta import ParamFieldInfo, ParamFieldType


_typed_map: Dict[ParamFieldType, str] = {
    ParamFieldType.STRING: 'str',
    ParamFieldType.INTEGER: 'int',
    ParamFieldType.FLOAT: 'float'
}


def create_sql_api(
        api_url: str,
        sql: str,
        params: Dict[str, ParamFieldInfo],
        depends_list: List[str],
        summary: str,
        desc: str
) -> str:
    id = int(datetime.now().timestamp() * 1000)
    # 生成 API 请求的 BaseModel class
    cls_code = ''
    if params:
        fields = [f'{arg_info["name"]}: {_typed_map.get(arg_info["typed"], "str")}' for _, arg_info in params.items()]
        cls_code = f'class DynamicArgs_{id}(BaseModel):\n    ' + '\n    '.join(fields) + '\n\n'
    # 生成 API 函数的参数
    func_param_list = []
    if params:
        func_param_list.append(f'args: DynamicArgs_{id} = Body()')
    func_param_list += depends_list
    func_params = ',\n    '.join(func_param_list)
    if func_params:
        func_params = '\n    ' + func_params + '\n'
    code = f"""{cls_code}
@app.post('/dynamic{api_url}', 
    response_model=R,
    summary='{summary}',
    description='{desc}',
    tags=['dynamic-api']
)
async def dynamic_api_{id}({func_params}):
    sql = f\"\"\"{sql}\"\"\"
    with Session(engine) as session:
        result = session.execute(text(sql))
    result = [row._asdict() for row in result]
    return R.success(result)
"""
    return code
