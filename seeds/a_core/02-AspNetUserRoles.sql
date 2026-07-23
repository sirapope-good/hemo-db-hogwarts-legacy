INSERT INTO local."AspNetUserRoles"(
	"UserId", "RoleId")
VALUES 
    -- 1. กลุ่ม HeadNurse (ได้ Role HeadNurse)
    ('4dbc7800-d343-4d6e-ab27-a7706b0cd126', 'baad21b1-6d08-4823-8cf3-0776a6266488'),
    ('ee7268d6-3012-4918-ad50-df59ac091c9d', 'baad21b1-6d08-4823-8cf3-0776a6266488'),
    -- + เพิ่ม Base Role 'Nurse' ให้ HeadNurse
    ('4dbc7800-d343-4d6e-ab27-a7706b0cd126', 'f903d36f-2531-4916-86bb-7b051aac7029'),
    ('ee7268d6-3012-4918-ad50-df59ac091c9d', 'f903d36f-2531-4916-86bb-7b051aac7029'),

    -- 2. กลุ่ม SpecialHD (ได้ Role SpecialHD)
    ('258a7d9f-5fa7-4eae-8d31-bb7f64d35a79', '9453a296-a401-a345-bf81-bca7ab0f73b5'),
    ('4875d3e5-9a6d-41c5-b3d5-7b4359c1baad', '9453a296-a401-a345-bf81-bca7ab0f73b5'),
    -- + เพิ่ม Base Role 'Nurse' ให้ SpecialHD
    ('258a7d9f-5fa7-4eae-8d31-bb7f64d35a79', 'f903d36f-2531-4916-86bb-7b051aac7029'),
    ('4875d3e5-9a6d-41c5-b3d5-7b4359c1baad', 'f903d36f-2531-4916-86bb-7b051aac7029'),

    -- 3. กลุ่ม PN (ได้ Role PN)
    ('ee44cb44-8886-4193-9a02-53fdad80e46e', '9453a296-a401-480b-bf81-bca7ab0f72a7'),
    ('7d26cfab-fb31-41cc-a4ea-29e610568be3', '9453a296-a401-480b-bf81-bca7ab0f72a7'),
    -- + เพิ่ม Base Role 'Nurse' ให้ PN
    ('ee44cb44-8886-4193-9a02-53fdad80e46e', 'f903d36f-2531-4916-86bb-7b051aac7029'),
    ('7d26cfab-fb31-41cc-a4ea-29e610568be3', 'f903d36f-2531-4916-86bb-7b051aac7029'),

    -- 4. กลุ่ม Doctor (คงเดิม)
    ('832bd9bf-6d52-4261-8eb0-80c3ca1fa1dd', 'a7c93a18-5c50-4e28-b02d-3b50cc3e17f1'),
    ('8090c38f-ca53-4238-810d-811a59e6cc68', 'a7c93a18-5c50-4e28-b02d-3b50cc3e17f1'),
    ('83ae307c-cd8c-4564-b0e8-da8d0b3f63fc', 'a7c93a18-5c50-4e28-b02d-3b50cc3e17f1'),
    ('ca5037bc-1ffb-4fcb-a5d0-495c3cd5aa99', 'a7c93a18-5c50-4e28-b02d-3b50cc3e17f1'),
    ('6e535885-692f-4f0c-b605-0d537154f835', 'a7c93a18-5c50-4e28-b02d-3b50cc3e17f1'),
    ('69c8793e-81ee-483a-ad47-ef1d3fa6337f', 'a7c93a18-5c50-4e28-b02d-3b50cc3e17f1'),
    ('367be69f-584a-49e4-a0b6-cab3635a9083', 'a7c93a18-5c50-4e28-b02d-3b50cc3e17f1'),
    ('638a7f0d-fe84-4256-b714-63071d9ce516', 'a7c93a18-5c50-4e28-b02d-3b50cc3e17f1'),
    ('de87de9b-5cac-4a3b-88f0-592f702048a5', 'a7c93a18-5c50-4e28-b02d-3b50cc3e17f1'),
    ('9c40de8c-0508-4381-a377-6a82c6304ed3', 'a7c93a18-5c50-4e28-b02d-3b50cc3e17f1'),
    ('a6049310-51eb-4aad-a499-1d335a0aef3b', 'a7c93a18-5c50-4e28-b02d-3b50cc3e17f1'),
    ('0322c1c8-5b34-4199-a0e2-81d08ab67a82', 'a7c93a18-5c50-4e28-b02d-3b50cc3e17f1'),

    -- 5. กลุ่ม Nurse ธรรมดา (คงเดิม)
    ('6ac9ae0c-53d1-497e-9e7d-3ce976d1f0d8', 'f903d36f-2531-4916-86bb-7b051aac7029'),
    ('eb8ed330-f3ab-4966-993c-2245653e075e', 'f903d36f-2531-4916-86bb-7b051aac7029');