"""Integration tests for all HR API endpoints."""


class TestRecruitmentAPI:
    def test_create(self, client):
        resp = client.post("/recruitments")
        assert resp.status_code == 201
        data = resp.json()
        assert "id" in data
        assert "created_at" in data

    def test_list(self, client):
        client.post("/recruitments")
        client.post("/recruitments")
        resp = client.get("/recruitments")
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    def test_get(self, client):
        created = client.post("/recruitments").json()
        resp = client.get(f"/recruitments/{created['id']}")
        assert resp.status_code == 200
        assert resp.json()["id"] == created["id"]

    def test_get_not_found(self, client):
        resp = client.get("/recruitments/999")
        assert resp.status_code == 404

    def test_delete(self, client):
        created = client.post("/recruitments").json()
        resp = client.delete(f"/recruitments/{created['id']}")
        assert resp.status_code == 204
        assert client.get(f"/recruitments/{created['id']}").status_code == 404

    def test_delete_not_found(self, client):
        resp = client.delete("/recruitments/999")
        assert resp.status_code == 404


class TestTalentAPI:
    def test_create(self, client):
        r_id = client.post("/recruitments").json()["id"]
        resp = client.post(f"/recruitments/{r_id}/talents", json={
            "email": "a@b.com", "real_name": "测试",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["email"] == "a@b.com"
        assert data["status"] == "new"

    def test_create_no_recruitment(self, client):
        resp = client.post("/recruitments/999/talents", json={
            "email": "a@b.com", "real_name": "测试",
        })
        assert resp.status_code == 404

    def test_list(self, client):
        r_id = client.post("/recruitments").json()["id"]
        client.post(f"/recruitments/{r_id}/talents", json={"email": "a@b.com", "real_name": "A"})
        client.post(f"/recruitments/{r_id}/talents", json={"email": "b@b.com", "real_name": "B"})
        resp = client.get(f"/recruitments/{r_id}/talents")
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    def test_list_filter_by_status(self, client):
        r_id = client.post("/recruitments").json()["id"]
        client.post(f"/recruitments/{r_id}/talents", json={"email": "a@b.com", "real_name": "A"})
        resp = client.get(f"/recruitments/{r_id}/talents", params={"status": "new"})
        assert len(resp.json()) == 1
        resp = client.get(f"/recruitments/{r_id}/talents", params={"status": "closed"})
        assert len(resp.json()) == 0

    def test_get(self, client):
        r_id = client.post("/recruitments").json()["id"]
        t_id = client.post(f"/recruitments/{r_id}/talents", json={
            "email": "a@b.com", "real_name": "测试",
        }).json()["id"]
        resp = client.get(f"/recruitments/{r_id}/talents/{t_id}")
        assert resp.status_code == 200
        assert resp.json()["real_name"] == "测试"

    def test_get_not_found(self, client):
        resp = client.get("/recruitments/999/talents/999")
        assert resp.status_code == 404

    def test_update(self, client):
        r_id = client.post("/recruitments").json()["id"]
        t_id = client.post(f"/recruitments/{r_id}/talents", json={
            "email": "a@b.com", "real_name": "测试",
        }).json()["id"]
        resp = client.patch(f"/recruitments/{r_id}/talents/{t_id}", json={"real_name": "新名字"})
        assert resp.status_code == 200
        assert resp.json()["real_name"] == "新名字"

    def test_delete(self, client):
        r_id = client.post("/recruitments").json()["id"]
        t_id = client.post(f"/recruitments/{r_id}/talents", json={
            "email": "a@b.com", "real_name": "测试",
        }).json()["id"]
        resp = client.delete(f"/recruitments/{r_id}/talents/{t_id}")
        assert resp.status_code == 204


class TestTransitionAPI:
    def test_new_to_contacted(self, client):
        r_id = client.post("/recruitments").json()["id"]
        t_id = client.post(f"/recruitments/{r_id}/talents", json={
            "email": "a@b.com", "real_name": "测试",
        }).json()["id"]
        resp = client.post(f"/recruitments/{r_id}/talents/{t_id}/transition", json={
            "status": "contacted",
        })
        assert resp.status_code == 200
        assert resp.json()["status"] == "contacted"

    def test_contacted_to_exam_sent(self, client):
        r_id = client.post("/recruitments").json()["id"]
        t_id = client.post(f"/recruitments/{r_id}/talents", json={
            "email": "a@b.com", "real_name": "测试",
        }).json()["id"]
        client.post(f"/recruitments/{r_id}/talents/{t_id}/transition", json={"status": "contacted"})
        resp = client.post(f"/recruitments/{r_id}/talents/{t_id}/transition", json={"status": "exam_sent"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "exam_sent"

    def test_invalid_transition_returns_400(self, client):
        r_id = client.post("/recruitments").json()["id"]
        t_id = client.post(f"/recruitments/{r_id}/talents", json={
            "email": "a@b.com", "real_name": "测试",
        }).json()["id"]
        resp = client.post(f"/recruitments/{r_id}/talents/{t_id}/transition", json={
            "status": "offer",
        })
        assert resp.status_code == 400

    def test_transition_with_sub_stage(self, client):
        r_id = client.post("/recruitments").json()["id"]
        t_id = client.post(f"/recruitments/{r_id}/talents", json={
            "email": "a@b.com", "real_name": "测试",
        }).json()["id"]
        resp = client.post(f"/recruitments/{r_id}/talents/{t_id}/transition", json={
            "status": "contacted", "sub_stage": "resume_passed",
        })
        assert resp.status_code == 200
        assert resp.json()["sub_stage"] == "resume_passed"


class TestSubStageAPI:
    def test_set_sub_stage(self, client):
        r_id = client.post("/recruitments").json()["id"]
        t_id = client.post(f"/recruitments/{r_id}/talents", json={
            "email": "a@b.com", "real_name": "测试",
        }).json()["id"]
        client.post(f"/recruitments/{r_id}/talents/{t_id}/transition", json={"status": "contacted"})
        resp = client.patch(f"/recruitments/{r_id}/talents/{t_id}/sub-stage", json={
            "sub_stage": "phone_interview",
        })
        assert resp.status_code == 200
        assert resp.json()["sub_stage"] == "phone_interview"

    def test_sub_stage_on_new_fails(self, client):
        r_id = client.post("/recruitments").json()["id"]
        t_id = client.post(f"/recruitments/{r_id}/talents", json={
            "email": "a@b.com", "real_name": "测试",
        }).json()["id"]
        resp = client.patch(f"/recruitments/{r_id}/talents/{t_id}/sub-stage", json={
            "sub_stage": "anything",
        })
        assert resp.status_code == 400


class TestPipelineAPI:
    def test_empty_pipeline(self, client):
        resp = client.get("/pipeline")
        assert resp.status_code == 200
        data = resp.json()
        assert "stages" in data
        assert "summary" in data
        assert data["summary"]["total"] == 0

    def test_pipeline_with_talents(self, seeded_client):
        resp = seeded_client.get("/pipeline")
        assert resp.status_code == 200
        data = resp.json()
        assert data["summary"]["total"] == 2
        assert data["summary"]["by_stage"]["interview"] == 1
        assert data["summary"]["by_stage"]["closed"] == 1

    def test_pipeline_stages_structure(self, seeded_client):
        resp = seeded_client.get("/pipeline")
        data = resp.json()
        for stage in ("new", "contacted", "exam_sent", "exam_received",
                      "evaluating", "interview", "offer", "closed"):
            assert stage in data["stages"]


class TestIngestAPI:
    def test_ingest_items(self, client):
        resp = client.post("/ingest", json={
            "source": "test",
            "items": [
                {
                    "message_id": "m1", "subject": "求职前端",
                    "sender_name": "张三", "sender_email": "zs@test.com",
                    "suggested_status": "contacted", "confidence": "high",
                },
            ],
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["queued"] == 1
        assert data["skipped"] == 0

    def test_ingest_duplicate_skipped(self, client):
        payload = {
            "source": "test",
            "items": [{
                "message_id": "dup1", "subject": "重复",
                "sender_name": "李四", "sender_email": "ls@test.com",
            }],
        }
        client.post("/ingest", json=payload)
        resp = client.post("/ingest", json=payload)
        assert resp.json()["skipped"] == 1
        assert resp.json()["queued"] == 0

    def test_ingest_multiple(self, client):
        resp = client.post("/ingest", json={
            "source": "test",
            "items": [
                {"message_id": "a", "subject": "S1", "sender_email": "a@t.com"},
                {"message_id": "b", "subject": "S2", "sender_email": "b@t.com"},
            ],
        })
        assert resp.json()["queued"] == 2


class TestQueueAPI:
    def test_list_empty(self, client):
        resp = client.get("/queue")
        assert resp.status_code == 200
        assert resp.json()["total"] == 0
        assert resp.json()["items"] == []

    def test_list_with_items(self, client):
        client.post("/ingest", json={
            "source": "test",
            "items": [{"message_id": "q1", "subject": "测试", "sender_email": "t@t.com"}],
        })
        resp = client.get("/queue")
        assert resp.json()["total"] == 1

    def test_confirm_queue_item(self, client):
        client.post("/ingest", json={
            "source": "test",
            "items": [{
                "message_id": "cq1", "subject": "确认测试",
                "sender_name": "王五", "sender_email": "ww@test.com",
                "suggested_status": "contacted",
            }],
        })
        queue_resp = client.get("/queue")
        qid = queue_resp.json()["items"][0]["queue_id"]
        resp = client.patch(f"/queue/{qid}/confirm", json={})
        assert resp.status_code == 200
        data = resp.json()
        assert data["action"] == "confirmed"
        assert data["talent_id"] is not None

    def test_ignore_queue_item(self, client):
        client.post("/ingest", json={
            "source": "test",
            "items": [{"message_id": "iq1", "subject": "忽略测试", "sender_email": "ig@t.com"}],
        })
        qid = client.get("/queue").json()["items"][0]["queue_id"]
        resp = client.patch(f"/queue/{qid}/ignore", json={})
        assert resp.status_code == 200
        assert resp.json()["action"] == "ignored"

    def test_confirm_not_found(self, client):
        resp = client.patch("/queue/999/confirm", json={})
        assert resp.status_code == 404

    def test_queue_stats(self, client):
        resp = client.get("/queue/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert "pending" in data


class TestPoolAPI:
    def test_list_pool_empty(self, client):
        resp = client.get("/pool")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_pool_with_data(self, seeded_client):
        resp = seeded_client.get("/pool")
        assert resp.status_code == 200
        items = resp.json()
        assert len(items) >= 1

    def test_pool_application(self, seeded_client):
        apps = seeded_client.get("/applications", params={"pooled": False}).json()
        active_apps = [a for a in apps if a.get("pooled_at") is None]
        if active_apps:
            app_id = active_apps[0]["id"]
            resp = seeded_client.post(f"/applications/{app_id}/pool")
            assert resp.status_code == 200
            assert resp.json()["pooled_at"] is not None

    def test_pool_twice(self, seeded_client):
        apps = seeded_client.get("/applications", params={"pooled": False}).json()
        active_apps = [a for a in apps if a.get("pooled_at") is None]
        if active_apps:
            app_id = active_apps[0]["id"]
            seeded_client.post(f"/applications/{app_id}/pool")
            resp = seeded_client.post(f"/applications/{app_id}/pool")
            assert resp.status_code == 200

    def test_pool_not_found(self, client):
        resp = client.post("/applications/999/pool")
        assert resp.status_code == 404

    def test_unpool_application(self, seeded_client):
        pooled = seeded_client.get("/pool").json()
        if pooled:
            app_id = pooled[0]["id"]
            r_id = pooled[0]["recruitment_id"]
            resp = seeded_client.post(f"/applications/{app_id}/unpool", json={
                "recruitment_id": r_id,
            })
            assert resp.status_code == 201
            assert resp.json()["pooled_at"] is None

    def test_unpool_not_pooled(self, seeded_client):
        apps = seeded_client.get("/applications", params={"pooled": False}).json()
        active_apps = [a for a in apps if a.get("pooled_at") is None]
        if active_apps:
            app_id = active_apps[0]["id"]
            resp = seeded_client.post(f"/applications/{app_id}/unpool", json={
                "recruitment_id": 1,
            })
            assert resp.status_code == 400


class TestApplicationAPI:
    def test_list(self, seeded_client):
        resp = seeded_client.get("/applications")
        assert resp.status_code == 200
        assert len(resp.json()) >= 2

    def test_list_filter_by_status(self, seeded_client):
        resp = seeded_client.get("/applications", params={"status": "interview"})
        assert all(a["status"] == "interview" for a in resp.json())

    def test_list_filter_pooled(self, seeded_client):
        pooled = seeded_client.get("/applications", params={"pooled": True}).json()
        assert all(a["pooled_at"] is not None for a in pooled)

    def test_list_filter_not_pooled(self, seeded_client):
        active = seeded_client.get("/applications", params={"pooled": False}).json()
        assert all(a["pooled_at"] is None for a in active)


class TestCandidateAPI:
    def test_list(self, seeded_client):
        resp = seeded_client.get("/candidates")
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    def test_applications(self, seeded_client):
        candidates = seeded_client.get("/candidates").json()
        cid = candidates[0]["id"]
        resp = seeded_client.get(f"/candidates/{cid}/applications")
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    def test_applications_not_found(self, client):
        resp = client.get("/candidates/999/applications")
        assert resp.status_code == 404


class TestHeadcountAPI:
    def test_headcount(self, seeded_client):
        r_id = seeded_client.get("/recruitments").json()[0]["id"]
        resp = seeded_client.get(f"/recruitments/{r_id}/headcount")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_offers" in data
        assert "accepted" in data

    def test_headcount_not_found(self, client):
        resp = client.get("/recruitments/999/headcount")
        assert resp.status_code == 404
