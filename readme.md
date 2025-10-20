# To Do List(문제)
- 랭그래프 실시간 업데이트 안되고, 다 끝나고 실행돼
- 로그인 만료 시간 4시간으로 설정
- 로그인 만료 됐을 때 액션이 생기면 자동으로 SSO 로그인 되어야하는데 안돼
- 크롭 탭에 나오는 로고 추가 : 경로(src/assets/images/logo.png)
- 증강된 키워드에 우상단 다 키워드로 나오는거 맞아?
- 사용자 별 대화 리스트 별도 관리 안돼
- 다른 사용자가 로그인되면 그 사용자로 덤프가 돼 (추가가 아니라)
-> foreign key 없이도 동작하도록

- 랭그래프 최후 답변이 "검색된 내용 기반 답변" 이 부분처럼 **나 엔터처리 정확히 되도록 그리고 가시성도 강화 / 
-> | 개선 항목 | 핵심 내용 |
|-----------|-----------|
이런 것도 표로
-> ### 큰 헤더
-> **~** 이건 중간 헤더

- 버튼 누르면 이미지 url 새 탭으로 띄워지게 (아니면 호버?)
- vue 디버깅 호환 되도록


# 정보
- 벡터부터 아래로 변경
콜렉션 Name : "RC"
Point 정보
vector : { "text":"aaa" "summary_purpose":"bbb" "summary_result":"ccc" "summary_fb":"ddd" },
 document_name : temp_title.pptx,
  image_url [ 0:"/appdata/RC/images/temp_title_whole.jpg" ] index_rdb : 3 

프론트에서 보여줄 이미지 경로
image_url에서 /appdata/RC/images/ 이걸 https://10.172.107.182로 대체
실제 이미지 url : https://10.172.107.182/imageview/temp_title_whole.jpg

