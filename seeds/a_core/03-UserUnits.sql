-- Option A: 2 units
--   -1 Hogwarts Hospital Wing — most staff
--    1 Azkaban Ward           — Vector, Grubbly-Plank, Binns (+ Sinistra / Sprout cross-cover)
INSERT INTO local."UserUnits"(
	"UserId", "UnitId")
	VALUES 
-- Hogwarts only
('4dbc7800-d343-4d6e-ab27-a7706b0cd126',-1), -- Dumbledore
('ee7268d6-3012-4918-ad50-df59ac091c9d',-1), -- McGonagall
('258a7d9f-5fa7-4eae-8d31-bb7f64d35a79',-1), -- Snape
('4875d3e5-9a6d-41c5-b3d5-7b4359c1baad',-1), -- Hagrid
('832bd9bf-6d52-4261-8eb0-80c3ca1fa1dd',-1), -- Lupin (Doctor)
('8090c38f-ca53-4238-810d-811a59e6cc68',-1), -- Sirius (Doctor)
('83ae307c-cd8c-4564-b0e8-da8d0b3f63fc',-1), -- Lockhart (Doctor)
('ca5037bc-1ffb-4fcb-a5d0-495c3cd5aa99',-1), -- Slughorn (Doctor)
('6ac9ae0c-53d1-497e-9e7d-3ce976d1f0d8',-1), -- Trelawney
('eb8ed330-f3ab-4966-993c-2245653e075e',-1), -- Flitwick
('ee44cb44-8886-4193-9a02-53fdad80e46e',-1), -- Filch
('7d26cfab-fb31-41cc-a4ea-29e610568be3',-1), -- Pomfrey
('6e535885-692f-4f0c-b605-0d537154f835',-1), -- Quirrell (Doctor)
('69c8793e-81ee-483a-ad47-ef1d3fa6337f',-1), -- Hooch (Doctor)
('367be69f-584a-49e4-a0b6-cab3635a9083',-1), -- Burbage (Doctor)

-- Azkaban Ward only
('638a7f0d-fe84-4256-b714-63071d9ce516', 1),  -- Vector (Doctor)
('de87de9b-5cac-4a3b-88f0-592f702048a5', 1),  -- Grubbly-Plank (Doctor)
('9c40de8c-0508-4381-a377-6a82c6304ed3', 1),  -- Binns (Doctor)

-- Cross-cover both units
('a6049310-51eb-4aad-a499-1d335a0aef3b', -1), -- Sinistra
('a6049310-51eb-4aad-a499-1d335a0aef3b', 1),
('0322c1c8-5b34-4199-a0e2-81d08ab67a82', -1), -- Sprout
('0322c1c8-5b34-4199-a0e2-81d08ab67a82', 1);
