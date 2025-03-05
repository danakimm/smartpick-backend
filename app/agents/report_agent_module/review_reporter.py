from app.agents.report_agent_module.utility_report import Node
import re
from .template_generator import ResultTemplate, Product, Reviews, Purchase_Info_Stores
from .bsae_reporter import BaseReporter
from .dummy import get_review_data_real_dummy


class ReviewReporter(BaseReporter):
    def __init__(self,input,query):
        script=[]
        script.append('현재 첫번째 시도입니다.')
        script.append('두번째 시도입니다. 다음 질문과 함꼐 다시 생각해 보세요,')
        script.append('세번째 시도입니다. 이전의 질의 응답과 함꼐 다시 생각해 보세요,')
        script.append('이번이 마지막 시도입니다. 이전의 질의 응답과 함꼐 다시 생각해 보세요, 이번엔 질문을 반환하지 않고 나머지 값을 최대한 채워서 반환합니다. 마지막 반환 시에는 반드시 데이터를 확인하고 채울 수 있는데 채우지 않은 항목이 있는지 꼼꼼히 확인합니다.')
        required_keyt=["general_users.total_reviews","general_users.positive_percentage","general_users.negative_percentage","general_users.positive_reviews","general_users.negative_reviews","general_users.negative_reviews","general_users.user_comments"]
        table_content="""
                            ### 🔹 일반 사용자 리뷰 (`general_users`)

                            | 입력 변수명 | 설명 | 입력 예시 |
                            |------------|------|----------|
                            | `general_users.total_reviews` | 총 리뷰 개수 | `1363` |
                            | `general_users.positive_percentage` | 긍정 리뷰 비율 | `"76%"` |
                            | `general_users.negative_percentage` | 부정 리뷰 비율 | `"24%"` |
                            | `general_users.positive_reviews` | 긍정적인 리뷰 예시 | `["디자인 예뻐요", "영상 볼 때 최고", "배터리 오래가요"]` |
                            | `general_users.negative_reviews` | 부정적인 리뷰 예시 | `["애플펜슬 문제", "가격 비쌈", "주사율 아쉬움"]` |
                            | `general_users.user_comments` | 실제 사용자 댓글 | `[{{"user0": "user1", "comment": "디자인은 예쁜데 가격이 너무 높아요."}}]` |

                            ---
            
                        """
        prompt=f""" 당신은 분석 전문가입니다 아주 조금의 데이터만으로 필요한 정보를 찾아내는 달인입니다.
                            이번에는 댓글에서 추출된 데이터로 유저 요청에 최대한 관련된 부분을 추려서 다음 양식의 테이블을 작성하려 합니다. 만약 유저가 유튜브 영상을찾거나 리뷰를 찾더라도 마찬가지입니다 당신은 전문가로써 어떤 부분에 관심이 있는지를 추적해서 
                            아래의 테이블의 내용을 채워야만 합니다.
                            {table_content}
                            <작성 규약>
                            0. 테이블에 입력할 정보를 A로 칭하고 이를 위해 제공한 정보를 B로 칭합니다. 
                            1. 첫번째 단계 유저 요청을 확인하고 A를 어떻게 구성할지 파악합니다. 또한 같이 들어온 질문이 있다면 이를 확인하고 문제해결에 도움이 될만한 답변을 찾습니다. 해당 답변은 [[answer::답변내용]]으로 반환합니다.
                            2. 두번째 단계 B를 분석하고 파악합니다. 어떤 정보를 활용가능한지 어떤정보는 불필요한지 정제하고 수집합니다.
                            3. 세번째 단계 2번의 결과를 이용하여 최대한 정밀하게 A를 구성합니다.
                            4. 3번의 결과에서 유저의 요청과 일치하지않는 부분을 확인합니다. 이에 대헤 스스로 의문점이 있는지 확인압니다.
                            4-1 정보가 부족하다고 판단되면 반드시 3회까지 스스로에게 질문을 던져서 정말로 그런지 단 한칸도 채울수 없는지 확인해서 최대한 정확한 정보를 제공합니다.질문은 다음양식으로 반환해야합니다. [[selfquestion::질문내용]]
                            4-2 스스로에게 던지는 질문임을 잊지 말고 질문을 반환합니다.
                            [최종 단계]
                            반환을 준비합니다. 반환은 두 종류중 하나를 선택 가능합니다. 
                            첫번쨰, 현재 결과가 미비하다고 느낀다면 최대 3회까지 스스로에게 질문을 던질 수 있습니다. 질문은 다음양식으로 반환해야합니다. [[selfquestion::질문내용]]
                            두번째, 현재 결과가 만족스럽다면 결과를 반환합니다. 결과는 다음 양식으로 반환해야합니다. 이양식은 최 우선적으로 절대적으로 지켜야 할 사항입니다. [[general_users.total_reviews::총 리뷰 개수]], [[general_users.positive_percentage::긍정 리뷰 비율]], 
                            [[general_users.negative_percentage::부정 리뷰 비율]], [[general_users.positive_reviews::긍정적인 리뷰 예시]], 
                            [[general_users.negative_reviews::부정적인 리뷰 예시]], [[general_users.user_comments::실제 사용자 댓글]]
                            최종적으로 비어있는 내용이있는지 확인합니다 만약 비어있는 내용이 있다면 스스로에게 질문을 던지고 질문은 다음양식으로 반환해야합니다. [[selfquestion::질문내용]] 내용이 완전하다면 질문은 반환하지 않습니다.질문은 매번 새로운 질문으로 변화를 줍니다.
                            최종 시도에서는 비어있는 내용이 있다 하더라도 질문은 반환하지 않고, 나머지 값은 그대로 출력합니다. 마지막 반환 시에는 반드시 데이터를 확인하고 채울 수 있는데 채우지 않은 항목이 있는지 꼼꼼히 확인합니다.
                            다시한번 해당항목들{required_keyt}이 모두 채워졌는지 확인하고 반환은 추가 문구 없이 결과한 반환합니다. 또한 위의 양식을 준수합니다.
                            """
        ##############################################
        data=input
        section1=[]
        section2=[]
        query=query
        model=Node(prompt)
        selfquestion=[]
        selfanswer=[]
        context=f"""
                    
                    다음은 테이블을 채우기 위해 제공되는 정보들입니다.
                    리뷰 집계 데이터:{data}

        """
        cachepath=".review_cache.h5"
        find_dict={data["product_name"].replace(" ",""):[]}
        cache_key=data["product_name"].replace(" ","")
        require_key=required_keyt
        reject_key=None
        #####################################################################
        super().__init__(
            data=data,
            section1=section1,
            section2=section2,
            table_content=table_content,
            prompt=prompt,
            query=query,
            model=model,
            script=script,
            selfquestion=selfquestion,
            selfanswer=selfanswer,
            context=context,
            cachepath=cachepath,
            find_dict=find_dict,
            cache_key=cache_key,
            require_key=require_key,
            reject_key=reject_key
        )
def get_general_users_dummy():
    return {
        "general_users.total_reviews": 1363,
        "general_users.positive_percentage": "76%",
        "general_users.negative_percentage": "24%",
        "general_users.positive_reviews": ["디자인 예뻐요", "영상 볼 때 최고", "배터리 오래가요"],
        "general_users.negative_reviews": ["애플펜슬 문제", "가격 비쌈", "주사율 아쉬움"],
        "general_users.user_comments": [
            {"user": "user1", "comment": "디자인은 예쁜데 가격이 너무 높아요."}
        ]
    }
async def test_review_main():
    input=get_review_data_real_dummy()
    query="애플의 아이패드 디지털 드로잉에 적합한 제품 리뷰 영상이 필요합니다. 우수한 펜 반응속도와 고급형 프로세서를 탑재한 제품에 관한 정보가 포함된 클립이 있으면 좋겠으며 예산은 100만원입니다. 이 영상에서는 해당 제품의 기능 요약 및 인상적인 장면, 사용자 리뷰 등의 정보를 제공해주길 원합니다."
    reporter=ReviewReporter(input,query)
    result,response=reporter.get_response()
    generator = ResultTemplate()
    result_dict = generator.dict
    item_review=Reviews()
    general_users=item_review.general_users
    try:
        general_users.process_dict(result[0])
        general_users.set_value(result_dict)
    except Exception as e:
        print(e)
        print(f"오류가 발생했습니다.반환값:{result[0]}")
    #import pprint
    #pprint.pprint(result_dict, width=150)
    return general_users, []

async def review_main(input,query):
    reporter=ReviewReporter(input,query)
    result,response=reporter.get_response()
    generator = ResultTemplate()
    result_dict = generator.dict
    item_review=Reviews()
    general_users=item_review.general_users
    try:
        general_users.process_dict(result[0])
        general_users.set_value(result_dict)
    except Exception as e:
        print(e)
        print(f"오류가 발생했습니다.반환값:{result[0]}")
    #import pprint
    #pprint.pprint(result_dict, width=150)
    return general_users, response


if __name__ == "__main__":
    import asyncio
    general_users, result=asyncio.run(test_review_main())
    generator = ResultTemplate()
    result_dict = generator.dict
    general_users.set_value(result_dict)
    import pprint
    pprint.pprint(result_dict, width=150)