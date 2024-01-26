# 정보
## 목적
뉴스 데이터를 통합 수집하여 개인이 뉴스를 검색할 수 있도록 제공한다.


## RSS
* [RSS란 무엇일까? RSS 2.0 스펙과 포맷](https://madplay.github.io/post/rss2-specification)

# 특이사항
## alembic
```shell
alembic init migrations
# 설정파일 수정 후
alembic revision --autogenerate
alembic upgrade head
```

# Todo
* [x] schema 수정
* [x] 검색 속도 개선


### 주의사항
* SQLite는 제약조건 변경을 지원하지 않는다.
* 오류 발생시 downgrade 후 직접 파일을 삭제하고 다시 생성할 것
* unique 속성 제거를 탐지하지 못함

## RSS Parser
### 주의사항
* snake case 자동변환 적용됨