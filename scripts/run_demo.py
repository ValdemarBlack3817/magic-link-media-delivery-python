from magic_link_service import Asset, build_creator_delivery


def main() -> None:
    job = build_creator_delivery(Asset("asset-42", "Spring lookbook", "creator@example.com"))
    print({"before": job.state, "after_process": job.process(), "after_delivery": job.deliver()})


if __name__ == "__main__":
    main()
