from app.agents.report_agent_module.utility_report import Node
import re
from .dummy import get_youtube_data_dummy
from .template_generator import ResultTemplate, Product, Reviews, Purchase_Info_Stores
from .bsae_reporter import BaseReporter

class YoutubeReporter(BaseReporter):
    def __init__(self,input,query):
        script=[]
        script.append('현재 첫번째 시도입니다.')
        script.append('두번째 시도입니다. 다음 질문과 함꼐 다시 생각해 보세요,')
        script.append('세번째 시도입니다. 이전의 질의 응답과 함꼐 다시 생각해 보세요,')
        require_key=["youtuber.views","youtuber.time_since_upload","youtuber.timestamp1","youtuber.timestamp1_description","youtuber.opinion","youtuber.opinion_reason","youtuber.pros","youtuber.cons","youtuber.link"]
        script.append('이번이 마지막 시도입니다. 이전의 질의 응답과 함꼐 다시 생각해 보세요, 이번엔 질문을 반환하지 않고 나머지 값을 최대한 채워서 반환합니다. 무슨일이있어도 질문과 통상적인 답변을 반환하지 않으며 지정된 형식의 출력만을 반환합니다. 자료가 모자라더라도 최대한 채워서 반환합니다.')
        table_content="""
                        ### 🔹 유튜버 리뷰 (`youtuber`)
                        | 입력 변수명 | 설명 | 입력 예시 |
                        |------------|------|----------|
                        | `youtuber.name` | 유튜버 이름 | `"UNDERkg"` |
                        | `youtuber.subscribers` | 구독자 수 | `"78.8만 명"` |
                        | `youtuber.title` | 리뷰 영상 제목 | `"끊이지 않는 마진, 아이패드 (10세대) 리뷰"` |
                        | `youtuber.views` | 조회수 | `"46만 회"` |
                        | `youtuber.time_since_upload` | 업로드 이후 시간 | `"2년 전"` |
                        | `youtuber.timestamp [1에서 6번까지 번호]` | 하이라이트 타임스탬프 1~6 | `"0:31"` |
                        | `youtuber.timestamp[1에서 6번까지 번호]_description` | 타임스탬프 1~6 설명 | `"디자인 및 외관 설명"` |
                        | `youtuber.opinion` | 유튜버 최종 의견 | `"추천하지 않음"` |
                        | `youtuber.opinion_reason` | 추천 또는 비추천 이유 | `"디자인은 좋으나, 가격이 너무 올라감"` |
                        | `youtuber.pros` | 장점 리스트 | `["새로운 디자인", "USB-C 도입"]` |
                        | `youtuber.cons` | 단점 리스트 | `["애플펜슬 1세대 지원", "가격 상승"]` |
                        | `youtuber.link` | 리뷰 영상 링크 | `"https://www.youtube.com/watch?v=1"` |
            
                        """
        prompt=f""" 당신은 분석 전문가입니다 아주 조금의 데이터만으로 필요한 정보를 찾아내는 달인입니다.
                            이번에는 유튜브자막데이터와 일부 메타데이터로  유저 요청에 알맞게 다음 양식의 테이블을 작성하려 합니다.
                            아래의 테이블을 작성해주세요.
                            {table_content}
                            <작성 규약>
                            0. 테이블에 입력할 정보를 A로 칭하고 이를 위해 제공한 정보를 B로 칭합니다. 
                            1. 첫번째 단계 유저 요청을 확인하고 A를 어떻게 구성할지 파악합니다. 또한 같이 들어온 질문이 있다면 이를 확인하고 문제해결에 도움이 될만한 답변을 찾습니다. 해당 답변은 [[answer::답변내용]]으로 반환합니다.
                            2. 두번째 단계 B를 분석하고 파악합니다. 어떤 정보를 활용가능한지 어떤정보는 불필요한지 정제하고 수집합니다.
                            3. 세번째 단계 2번의 결과를 이용하여 최대한 정밀하게 A를 구성합니다.
                            3-1. youtuber.timestamp[번호]_description  섹션의 내용은 5~ 10단어로 구성합니다.
                            4. 3번의 결과에서 유저의 요청과 일치하지않는 부분을 확인합니다. 이에 대헤 스스로 의문점이 있는지 확인압니다.
                            4-1 정보가 부족하다고 판단되면 반드시 3회까지 스스로에게 질문을 던져서 정말로 그런지 단 한칸도 채울수 없는지 확인해서 최대한 정확한 정보를 제공합니다.질문은 다음양식으로 반환해야합니다. [[selfquestion::질문내용]]
                            4-2 스스로에게 던지는 질문임을 잊지 말고 질문을 반환합니다.
                            [최종 단계]
                            반환을 준비합니다. 반환은 두 종류중 하나를 선택 가능합니다. 
                            첫번쨰, 현재 결과가 미비하다고 느낀다면 최대 3회까지 스스로에게 질문을 던질 수 있습니다. 질문은 다음양식으로 반환해야합니다. [[selfquestion::질문내용]]
                            두번째, 현재 결과가 만족스럽다면 결과를 반환합니다. 결과는 다음 양식으로 반환해야합니다. [[youtuber.name::유튜버 이름 결과]],[[youtuber.subscribers::구독자 수 결과]],[[youtuber.title::리뷰 영상 제목 결과]],
                            [[youtuber.views::조회수 결과]],[[youtuber.time_since_upload::업로드 이후 시간 결과]],[[youtuber.timestamp1::하이라이트 타임스탬프 1 결과]],
                            [[youtuber.timestamp1_description::타임스탬프 1 설명 결과]],[[youtuber.timestamp2::하이라이트 타임스탬프 2 결과]],[[youtuber.timestamp2_description::타임스탬프 2 설명 결과]],[[youtuber.timestamp3:하이라이트 타임스탬프 3 결과]],[[youtuber.timestamp3_description::타임스탬프 3 설명 결과]]
                            ,[[youtuber.timestamp4::하이라이트 타임스탬프 4 결과]],[[youtuber.timestamp4_description::타임스탬프 4 설명 결과]],[[youtuber.timestamp5:하이라이트 타임스탬프 5 결과]],[[youtuber.timestamp5_description::타임스탬프 5 설명 결과]],[[youtuber.timestamp6:하이라이트 타임스탬프 6 결과]],[[youtuber.timestamp6_description::타임스탬프 6 설명 결과]]
                            ,[[youtuber.opinion::유튜버 최종 의견 결과]],[[youtuber.opinion_reason::추천 또는 비추천 이유 결과]],
                            [[youtuber.pros::장점 리스트 결과]],[[youtuber.cons::단점 리스트 결과]],[[youtuber.link::리뷰 영상 링크 결과]]
                            최종적으로 비어있는 내용이있는지 확인합니다 만약 비어있는 내용이 있다면 스스로에게 질문을 던지고 질문은 다음양식으로 반환해야합니다. [[selfquestion::질문내용]] 내용이 완전하다면 질문은 반환하지 않습니다.질문은 매번 새로운 질문으로 변화를 줍니다.
                            최종 시도에서는 비어있는 내용이 있다 하더라도 질문은 반환하지 않고, 나머지 값은 그대로 출력합니다.특히 {require_key}의 내용은 반드시 더 신경써서 채워야 합니다.
                            반환은 추가 문구 없이 결과한 반환합니다.
                            해당 양식이 완전하지 않거나 길다고 생략하면 뒤의 파싱 로직이 완전히 망가지기때문에 "절대적으로" 준수해야함
                            """
        
        data=input['youtube']
        section1=input['youtube']['raw_meta_data']
        section1['자막']=section1['자막'].replace("\n\n","")
        section2=input['youtube']['llm_process_data']
        query=query
        model=Node(prompt)
        selfquestion=[]
        selfanswer=[]
        context=f"""
                    
                    다음은 테이블을 채우기 위해 제공되는 정보들입니다.
                    video_metadata:{data['raw_meta_data']}
                    LLM_process_data:{data['llm_process_data']}
        """
        cachepath="youtube_cache.h5"
        find_dict={section1["제목"].replace(" ",""):[]}
        cache_key=section1["제목"].replace(" ","")
        reject_key=None
        
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
async def test_youtube_main():
    input=get_youtube_data_dummy()
    reporter=YoutubeReporter(input)
    result,response=reporter.get_response()
    item_review=Reviews()
    youtuber=item_review.youtuber
    try:
        youtuber.process_dict(result[0])
    except Exception as e:
        print(e)
        print(f"오류가 발생했습니다.반환값:{result[0]}")
    return youtuber, result
async def youtube_main(input,query):
    reporter=YoutubeReporter(input,query)
    result,response=reporter.get_response()
    item_review=Reviews()
    youtuber=item_review.youtuber
    try:
        youtuber.process_dict(result[0])
    except Exception as e:
        print(e)
        print(f"오류가 발생했습니다.반환값:{result[0]}")
    return youtuber, result



if __name__ == "__main__":
    youtuber, result=test_youtube_main()
    generator = ResultTemplate()
    result_dict = generator.dict
    youtuber.set_value(result_dict)
    import pprint
    pprint.pprint(result_dict, width=150)